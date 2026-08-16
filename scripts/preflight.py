#!/usr/bin/env python3
"""
store-ready pre-flight audit.

Read-only. Parses a mobile project's manifests and config files and reports what
can be determined mechanically before a store submission.

Usage:
    python3 preflight.py /path/to/project [--json]

Exit codes:
    0  no blockers found
    1  at least one BLOCKER
    2  the path is not a recognisable mobile project

Standard library only. No network access. Never writes to the project.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BLOCKER, WARN, INFO = "BLOCKER", "WARN", "INFO"

ANDROID_NS = "{http://schemas.android.com/apk/res/android}"

# Manifest components that need an explicit android:exported once they declare
# an intent filter (Android 12+).
EXPORTABLE_COMPONENTS = ("activity", "activity-alias", "service", "receiver", "provider")

# Permissions that require a declaration form or are commonly refused.
SENSITIVE_ANDROID_PERMISSIONS = {
    "android.permission.QUERY_ALL_PACKAGES": "Declaration required; usually refused. Prefer a <queries> element.",
    "android.permission.MANAGE_EXTERNAL_STORAGE": "Declaration + demo video required. Prefer scoped storage or SAF.",
    "android.permission.SYSTEM_ALERT_WINDOW": "Needs justification; restricted on recent Android versions.",
    "android.permission.REQUEST_INSTALL_PACKAGES": "Declaration required.",
    "android.permission.ACCESS_BACKGROUND_LOCATION": "Declaration + video showing background use.",
    "android.permission.READ_SMS": "Restricted to default SMS handlers. Use the SMS Retriever API for OTP.",
    "android.permission.RECEIVE_SMS": "Restricted to default SMS handlers.",
    "android.permission.READ_CALL_LOG": "Restricted to default dialer apps.",
    "android.permission.PROCESS_OUTGOING_CALLS": "Restricted; deprecated.",
    "android.permission.SCHEDULE_EXACT_ALARM": "Restricted to alarm/calendar apps.",
    "android.permission.USE_FULL_SCREEN_INTENT": "Restricted to calls and alarms.",
    "android.permission.ACCESS_FINE_LOCATION": "Needs a visible, user-facing feature.",
    "android.permission.READ_CONTACTS": "Needs a visible, user-facing feature.",
    "android.permission.RECORD_AUDIO": "Needs a visible, user-facing feature.",
    "android.permission.CAMERA": "Needs a visible, user-facing feature.",
}

# iOS API surface -> the Info.plist key it requires.
#
# Match native API symbols and package identifiers only. A bare English noun
# ("camera", "calendar", "contacts") matches icon asset names, route names and
# UI labels, and every match here is reported as a BLOCKER — so a false positive
# costs the user a purpose string for an API they never call, which is itself a
# Guideline 5.1.1 rejection. Prefer missing a detection over inventing one.
IOS_USAGE_KEYS = {
    "NSCameraUsageDescription": ("camera", (
        r"AVCaptureDevice|AVCaptureSession|UIImagePickerController"
        r"|package:camera/|image_picker"
        r"|expo-camera|expo-image-picker"
        r"|react-native-vision-camera|react-native-camera|react-native-image-picker"
        r"|@capacitor/camera")),
    "NSMicrophoneUsageDescription": ("microphone", (
        r"AVAudioRecorder|AVAudioEngine|requestRecordPermission"
        r"|flutter_sound|package:record/|speech_to_text"
        r"|expo-audio|react-native-audio-record|react-native-webrtc"
        r"|@capacitor-community/voice-recorder")),
    "NSPhotoLibraryUsageDescription": ("photo library", (
        r"PHPhotoLibrary|PHPickerViewController|PHAsset|UIImageWriteToSavedPhotosAlbum"
        r"|image_picker|photo_manager|image_gallery_saver"
        r"|expo-media-library|expo-image-picker"
        r"|react-native-image-picker|camera-roll|CameraRoll"
        r"|@capacitor/camera")),
    "NSLocationWhenInUseUsageDescription": ("location", (
        r"CLLocationManager|requestWhenInUseAuthorization"
        r"|geolocator|package:location/"
        r"|expo-location"
        r"|react-native-geolocation|@react-native-community/geolocation"
        r"|background-geolocation|@capacitor/geolocation|navigator\.geolocation")),
    "NSContactsUsageDescription": ("contacts", (
        r"CNContactStore|CNContactPicker|ABAddressBook"
        r"|flutter_contacts|contacts_service"
        r"|expo-contacts|react-native-contacts|@capacitor-community/contacts")),
    "NSCalendarsUsageDescription": ("calendar", (
        r"EKEventStore|EKEventEditViewController"
        r"|device_calendar|add_2_calendar"
        r"|expo-calendar|react-native-calendar-events")),
    "NSBluetoothAlwaysUsageDescription": ("bluetooth", (
        r"CBCentralManager|CBPeripheralManager"
        r"|flutter_blue|flutter_reactive_ble"
        r"|react-native-ble-plx|react-native-ble-manager|bluetooth-le")),
    "NSFaceIDUsageDescription": ("Face ID", (
        r"LAContext|deviceOwnerAuthenticationWithBiometrics"
        r"|local_auth|expo-local-authentication"
        r"|react-native-biometrics|react-native-touch-id")),
    "NSUserTrackingUsageDescription": ("tracking / IDFA", (
        r"ATTrackingManager|AppTrackingTransparency|ASIdentifierManager|advertisingIdentifier"
        r"|app_tracking_transparency|expo-tracking-transparency|react-native-tracking-transparency"
        r"|google_mobile_ads|react-native-google-mobile-ads|appsflyer")),
    "NSHealthShareUsageDescription": ("HealthKit", (
        r"HKHealthStore|HKQuantityType|HKObjectType"
        r"|package:health/|healthkit|react-native-health")),
    "NSSpeechRecognitionUsageDescription": ("speech recognition", (
        r"SFSpeechRecognizer|SFSpeechAudioBuffer"
        r"|speech_to_text|expo-speech-recognition|react-native-voice")),
}

# Credentials that grant power a client should never hold. Each is a BLOCKER.
# The PEM pattern requires an actual key body, so a source line such as
# `.replace('-----BEGIN PRIVATE KEY-----', '')` no longer matches the delimiter
# alone. It accepts `\n` escapes too, because service-account keys pasted into
# JavaScript and Dart carry escaped newlines rather than real ones.
SECRET_PATTERNS = [
    (r"sk_live_[0-9a-zA-Z]{16,}", "Stripe live secret key"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key id"),
    (r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----(?:\\n|[\r\n])+[A-Za-z0-9+/=\s\\]{100,}", "Private key"),
    (r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*[\"'][^\"'\s]{16,}[\"']", "Hard-coded credential"),
]

# Client-side Google API keys (Firebase, Maps) ship inside every APK and IPA by
# design — Google documents them as non-secret. They cannot be moved server-side
# because the SDK needs them to initialise, so reporting them as a leaked
# credential asks the user to do something impossible. They are still worth a
# warning, because an *unrestricted* key is a billing and abuse problem.
GOOGLE_API_KEY_PATTERN = r"AIza[0-9A-Za-z_\-]{35}"

# A matched "credential" that is obviously a template value, not a real one.
PLACEHOLDER_VALUE = re.compile(r"(?i)your[_-]?|xxx+|change[_-]?me|placeholder|todo|<[^>]{1,40}>|\.\.\.")

# The generic credential pattern only requires 16+ non-space characters after a
# name like `password` or `token`, so asset paths, routes and URLs match it —
# `imagePassword = 'assets/images/password.svg'` is not a leaked secret.
NON_CREDENTIAL_VALUE = re.compile(
    r"(?i)^(?:https?://|/|\.{1,2}/|assets?/|images?/|packages/|lib/|api/)"
    r"|\.(?:svg|png|jpe?g|webp|gif|json|dart|ya?ml|ttf|otf|mp[34]|html)$"
    r"|/$"  # a trailing slash means a route fragment, e.g. 'forgot-password/'
)

SCAN_EXTENSIONS = {".dart", ".kt", ".java", ".swift", ".m", ".mm", ".js", ".jsx", ".ts", ".tsx"}
SKIP_DIRS = {"build", ".git", "node_modules", "Pods", ".dart_tool", "vendor", ".gradle", "DerivedData"}

# Xcode target directories that are not the shipped application.
NON_APP_TARGET = re.compile(r"(?i)^.*(tests?|uitests?|extension|widget|watchkit|notificationservice|shareext|intents).*$")

# Purpose strings that say nothing, whatever their length.
PLACEHOLDER_PURPOSE = {"", "todo", "tbd", "xxx", "test", "description", "permission", "n/a", "none"}

# Apple's required-reason API categories, as they appear in native source.
REQUIRED_REASON_APIS = re.compile(
    r"UserDefaults|NSUserDefaults|systemUptime|mach_absolute_time"
    r"|\.modificationDate|\.creationDate|attributesOfItem"
    r"|volumeAvailableCapacity|activeInputModes|\bstat\("
)

_SOURCE_CACHE: dict[Path, list] = {}


class Report:
    def __init__(self) -> None:
        self.findings: list[dict] = []
        self.facts: dict = {}

    def add(self, level: str, message: str, where: str = "", fix: str = "") -> None:
        self.findings.append({"level": level, "message": message, "where": where, "fix": fix})

    def fact(self, key: str, value) -> None:
        self.facts[key] = value

    @property
    def blockers(self) -> int:
        return sum(1 for f in self.findings if f["level"] == BLOCKER)


# --------------------------------------------------------------------------- #
# stack detection
# --------------------------------------------------------------------------- #

def detect_stack(root: Path) -> list[str]:
    stacks = []
    if (root / "pubspec.yaml").exists():
        stacks.append("flutter")
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8", errors="ignore"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            if "expo" in deps:
                stacks.append("expo")
            if "react-native" in deps:
                stacks.append("react-native")
            if any(k.startswith("@capacitor/") for k in deps):
                stacks.append("capacitor")
        except (ValueError, OSError):
            pass
    if list(root.glob("**/ProjectSettings/ProjectSettings.asset")):
        stacks.append("unity")
    if not stacks:
        if list(root.glob("**/*.xcodeproj")) or list(root.glob("**/*.xcworkspace")):
            stacks.append("native-ios")
        if (root / "settings.gradle").exists() or (root / "settings.gradle.kts").exists():
            stacks.append("native-android")
    return stacks


def find_file(root: Path, *candidates: str) -> Path | None:
    for c in candidates:
        matches = [p for p in root.glob(c) if not any(part in SKIP_DIRS for part in p.parts)]
        if matches:
            return sorted(matches, key=lambda p: len(p.parts))[0]
    return None


# --------------------------------------------------------------------------- #
# android
# --------------------------------------------------------------------------- #

def audit_manifest_exported(text: str, rel: str, rep: Report) -> None:
    """Report every component that declares an intent filter without android:exported."""
    try:
        manifest = ET.fromstring(text)
    except ET.ParseError as exc:
        rep.add(WARN, f"AndroidManifest.xml could not be parsed ({exc})", rel,
                "Fix the XML, then re-run. Until then, check android:exported by hand on "
                "every component that declares an intent-filter.")
        return

    application = manifest.find("application")
    if application is None:
        return

    for element in application:
        if element.tag not in EXPORTABLE_COMPONENTS:
            continue
        if element.find("intent-filter") is None:
            continue
        if ANDROID_NS + "exported" in element.attrib:
            continue
        name = element.get(ANDROID_NS + "name", "unnamed")
        # ElementTree drops line numbers; recover one so the finding is clickable.
        anchor = re.search(rf'android:name="{re.escape(name)}"', text)
        where = f"{rel}:{text[: anchor.start()].count(chr(10)) + 1}" if anchor else rel
        rep.add(BLOCKER, f"<{element.tag}> {name} declares an intent-filter but no android:exported",
                where, "Set android:exported explicitly; required since Android 12.")


def audit_android(root: Path, rep: Report) -> None:
    manifest = find_file(root, "**/src/main/AndroidManifest.xml", "**/AndroidManifest.xml")
    if manifest is None:
        return
    rel = str(manifest.relative_to(root))
    text = manifest.read_text(encoding="utf-8", errors="ignore")

    perms = sorted(set(re.findall(r'uses-permission[^>]*android:name="([^"]+)"', text)))
    rep.fact("android_permissions", perms)
    for p in perms:
        if p in SENSITIVE_ANDROID_PERMISSIONS:
            rep.add(WARN, f"Sensitive permission declared: {p}", rel, SENSITIVE_ANDROID_PERMISSIONS[p])

    if 'android:debuggable="true"' in text:
        rep.add(BLOCKER, "Manifest sets android:debuggable=\"true\"", rel,
                "Remove it; debuggable release builds are rejected.")
    if 'android:usesCleartextTraffic="true"' in text:
        rep.add(WARN, "Cleartext HTTP traffic is enabled", rel,
                "Use HTTPS, or scope the exception with a network security config.")
    if "android:allowBackup" not in text:
        rep.add(INFO, "android:allowBackup is not set explicitly", rel,
                "Set it deliberately and exclude sensitive files from backup.")

    # Components with an intent filter but no explicit android:exported.
    # Parsed, not regexed: a self-closing component followed by a block one makes
    # any non-greedy `<tag>.*?</tag>` span two elements, which both hides the real
    # offender and reports a compliant one in its place.
    audit_manifest_exported(text, rel, rep)

    gradle = find_file(root, "**/app/build.gradle", "**/app/build.gradle.kts")
    if gradle is None:
        rep.add(WARN, "app/build.gradle not found", "", "Verify the Android module layout.")
        return
    grel = str(gradle.relative_to(root))
    g = gradle.read_text(encoding="utf-8", errors="ignore")

    def grab(key: str):
        m = re.search(rf"{key}\s*[= ]\s*['\"]?(\d+)['\"]?", g)
        return int(m.group(1)) if m else None

    target = grab("targetSdkVersion") or grab("targetSdk")
    minimum = grab("minSdkVersion") or grab("minSdk")
    rep.fact("target_sdk", target)
    rep.fact("min_sdk", minimum)

    if target is None:
        # The stock Flutter template writes `targetSdk = flutter.targetSdkVersion`
        # (or `targetSdkVersion flutter.targetSdkVersion`), which resolves only at
        # build time. Warning about it flags every compliant Flutter project.
        if re.search(r"targetSdk(Version)?\s*[= ]\s*flutter\.targetSdkVersion", g):
            rep.add(INFO, "targetSdk is inherited from the Flutter SDK", grel,
                    "It cannot be read statically. Run './gradlew -p android :app:properties | "
                    "grep targetSdk' and compare the result against Play's current requirement.")
        else:
            rep.add(WARN, "targetSdk could not be determined", grel,
                    "Set it explicitly and check Google Play's current required level.")
    else:
        rep.add(INFO, f"targetSdk = {target}", grel,
                "Compare against Play's current requirement — it rises every August.")

    appid = re.search(r"applicationId\s*[= ]\s*['\"]([^'\"]+)['\"]", g)
    if appid:
        rep.fact("application_id", appid.group(1))
        if any(t in appid.group(1) for t in ("com.example", "com.mycompany", "io.ionic.starter")):
            rep.add(BLOCKER, f"Placeholder applicationId: {appid.group(1)}", grel,
                    "The applicationId is permanent after first upload. Change it now.")

    if "signingConfigs" not in g:
        rep.add(WARN, "No signingConfigs block found", grel,
                "Release builds must be signed with a release key, not the debug key.")
    if re.search(r"signingConfig\s+signingConfigs\.debug", g):
        rep.add(BLOCKER, "Release build type uses the debug signing config", grel,
                "Configure a release keystore and enable Play App Signing.")
    if re.search(r"(storePassword|keyPassword)\s*[= ]\s*['\"]", g):
        rep.add(BLOCKER, "Keystore password is hard-coded in the Gradle file", grel,
                "Move it to key.properties or CI secrets and gitignore the file.")


# --------------------------------------------------------------------------- #
# ios
# --------------------------------------------------------------------------- #

def is_ios_app_plist(path: Path) -> bool:
    """True unless the plist belongs to a test bundle, app extension or framework."""
    parts = path.parts[:-1]
    if any(p in SKIP_DIRS for p in parts):
        return False
    if any(p.endswith((".framework", ".xcframework", ".dSYM", ".appex")) for p in parts):
        return False
    if "macos" in parts:
        return False
    return not any(NON_APP_TARGET.search(p) for p in parts)


def find_app_info_plist(root: Path) -> Path | None:
    """Locate the *application* Info.plist.

    The previous shortest-path heuristic tied on `ios/MyApp/Info.plist` and
    `ios/MyAppTests/Info.plist`, so the winner was directory order — and a test
    bundle's plist declares no purpose strings, which fabricated blockers while
    hiding the real ones.
    """
    candidates = [p for p in root.glob("**/Info.plist") if is_ios_app_plist(p)]
    if not candidates:
        return None

    def rank(path: Path):
        try:
            is_app = "<string>APPL</string>" in path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            is_app = False
        return (0 if is_app else 1, len(path.parts), str(path))

    return sorted(candidates, key=rank)[0]


def purpose_string_weight(value: str) -> float:
    """Approximate how much a purpose string actually says.

    A plain codepoint count treats `写真の撮影に使用します` — a complete sentence
    Apple accepts — as an 11-character placeholder. CJK and Hangul carry far
    more meaning per codepoint than Latin script does.
    """
    weight = 0.0
    for char in value:
        code = ord(char)
        if 0x3000 <= code <= 0x9FFF or 0xAC00 <= code <= 0xD7AF or 0xF900 <= code <= 0xFAFF:
            weight += 2.5
        else:
            weight += 1.0
    return weight


def audit_ios(root: Path, rep: Report) -> None:
    plist = find_app_info_plist(root)
    if plist is None:
        return
    rel = str(plist.relative_to(root))
    text = plist.read_text(encoding="utf-8", errors="ignore")

    declared = set(re.findall(r"<key>(NS\w+UsageDescription)</key>", text))
    rep.fact("ios_usage_descriptions", sorted(declared))

    source_blob = read_sources(root)
    for key, (feature, pattern) in IOS_USAGE_KEYS.items():
        used = re.search(pattern, source_blob, re.IGNORECASE) is not None
        if used and key not in declared:
            rep.add(BLOCKER, f"Code appears to use {feature} but {key} is missing", rel,
                    f"Add {key} with a user-facing reason, or remove the API usage.")

    for key in declared:
        m = re.search(rf"<key>{key}</key>\s*<string>([^<]*)</string>", text)
        value = (m.group(1) if m else "").strip()
        looks_placeholder = (value.lower().strip(" .") in PLACEHOLDER_PURPOSE
                             or value.lower() == key.lower())
        if looks_placeholder or purpose_string_weight(value) < 15:
            rep.add(BLOCKER, f"{key} has a placeholder or too-short purpose string", rel,
                    "Explain the user benefit concretely, e.g. 'Take a photo of your receipt to attach it'.")

    if "ITSAppUsesNonExemptEncryption" not in text:
        rep.add(WARN, "ITSAppUsesNonExemptEncryption is not declared", rel,
                "Declare it to avoid an export-compliance prompt on every upload.")

    bg = re.search(r"<key>UIBackgroundModes</key>\s*<array>(.*?)</array>", text, re.DOTALL)
    if bg:
        modes = re.findall(r"<string>([^<]+)</string>", bg.group(1))
        rep.fact("ios_background_modes", modes)
        rep.add(WARN, f"Background modes declared: {', '.join(modes)}", rel,
                "Each mode must map to real functionality a reviewer can observe.")

    manifests = [p for p in root.glob("**/PrivacyInfo.xcprivacy")
                 if not any(d in p.parts for d in SKIP_DIRS) and "macos" not in p.parts]
    if manifests:
        rep.fact("privacy_manifest", str(manifests[0].relative_to(root)))
        return

    # Apple requires an app-level privacy manifest when your *own* native code
    # touches a required-reason API. Bundled SDKs ship their own manifests, so an
    # app whose only such usage lives in plugins does not need one — calling that
    # "submission will be rejected" is simply false.
    native = "\n".join(t for p, t in read_source_files(root) if p.suffix in {".swift", ".m", ".mm"})
    if REQUIRED_REASON_APIS.search(native):
        rep.add(BLOCKER, "Native code uses a required-reason API but there is no PrivacyInfo.xcprivacy", "ios/",
                "Add a privacy manifest declaring the data types and the required-reason API codes.")
    else:
        rep.add(WARN, "No app-level PrivacyInfo.xcprivacy found", "ios/",
                "Required only if your own native code uses a required-reason API (UserDefaults, "
                "file timestamps, disk space, boot time, active keyboards) or you collect data. "
                "Bundled SDKs ship their own. Generate Xcode's privacy report to confirm.")


def read_source_files(root: Path, limit: int = 1200) -> list[tuple[Path, str]]:
    """Read the project's scannable sources once, then serve them from cache.

    Several audits need the same corpus; re-walking the tree per audit doubled
    the wall-clock cost and the peak memory on any large repository.
    """
    cached = _SOURCE_CACHE.get(root)
    if cached is not None:
        return cached
    files: list[tuple[Path, str]] = []
    for path in root.rglob("*"):
        if len(files) >= limit:
            break
        if path.is_dir() or path.suffix not in SCAN_EXTENSIONS:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            files.append((path, path.read_text(encoding="utf-8", errors="ignore")))
        except OSError:
            continue
    _SOURCE_CACHE[root] = files
    return files


def read_sources(root: Path, limit: int = 1200) -> str:
    return "\n".join(text for _, text in read_source_files(root, limit))


# --------------------------------------------------------------------------- #
# cross-cutting
# --------------------------------------------------------------------------- #

def audit_versions(root: Path, rep: Report) -> None:
    pub = root / "pubspec.yaml"
    if pub.exists():
        m = re.search(r"^version:\s*(\S+)", pub.read_text(encoding="utf-8", errors="ignore"), re.MULTILINE)
        if m:
            rep.fact("version", m.group(1))
            if m.group(1).startswith("1.0.0+1"):
                rep.add(INFO, "Version is still the template default (1.0.0+1)", "pubspec.yaml",
                        "Fine for a first release; the build number must increase on every upload.")


def is_false_credential(match: str) -> bool:
    """True when a SECRET_PATTERNS match is not actually a leaked credential."""
    if PLACEHOLDER_VALUE.search(match):
        return True
    quoted = re.findall(r"[\"']([^\"'\s]{8,})[\"']", match)
    if not quoted:
        return False
    value = quoted[-1]
    if re.match(GOOGLE_API_KEY_PATTERN, value):
        return True  # a client-side Google key; reported separately as a warning
    return bool(NON_CREDENTIAL_VALUE.search(value))


def audit_secrets(root: Path, rep: Report) -> None:
    hits, google_keys = [], []
    for path, content in read_source_files(root):
        where = str(path.relative_to(root))
        m = re.search(GOOGLE_API_KEY_PATTERN, content)
        if m:
            google_keys.append(f"{where}:{content[: m.start()].count(chr(10)) + 1}")
        for pattern, label in SECRET_PATTERNS:
            # Take the first match that survives filtering, not merely the first
            # match: a file can hold five client-side keys and one real secret.
            m = next((c for c in re.finditer(pattern, content)
                      if not is_false_credential(c.group(0))), None)
            if m:
                hits.append((label, f"{where}:{content[: m.start()].count(chr(10)) + 1}"))
                break
    for label, where in hits[:20]:
        rep.add(BLOCKER, f"Possible {label} committed in source", where,
                "Rotate the credential and move it server-side; binaries are trivially unpacked.")
    for where in google_keys[:5]:
        rep.add(WARN, "Client-side Google API key in source", where,
                "Expected — the SDK needs it and it ships in the binary either way. Do not try to "
                "move it server-side. Restrict it in Google Cloud Console (application restrictions "
                "plus an API allowlist) and enable Firebase App Check.")


def audit_policy_surface(root: Path, rep: Report) -> None:
    blob = read_sources(root)
    # Creating an account triggers the deletion requirement. Signing in does not:
    # a B2B app with admin-provisioned accounts, or one that only offers a login,
    # is not covered by Apple 5.1.1(v).
    creates_account = re.search(
        r"signUp|createUser|createUserWithEmail|registerUser"
        r"|signInWithOAuth|signInWithProvider|signInWithGoogle|signInWithApple", blob)
    login_only = re.search(r"signInWithPassword|signInWithEmailAndPassword|signInAnonymously", blob)
    has_delete = re.search(
        r"(?i)(delete|remove|close|destroy|terminate)[_\- ]?(my[_\- ]?)?(account|user|profile)"
        r"|deleteUser|account[_\- ]?deletion", blob)

    if creates_account and not has_delete:
        rep.add(BLOCKER, "Account creation found but no account-deletion path detected", "source",
                "Both stores require in-app account deletion plus a public web deletion URL.")
    elif login_only and not has_delete:
        rep.add(WARN, "Sign-in found, but no account-deletion path and no sign-up either", "source",
                "If users can create an account anywhere — in the app, on your site, or through an "
                "admin — both stores require in-app deletion. Only accounts you provision yourself "
                "and users cannot self-create are exempt.")

    if re.search(r"WebView|InAppWebView|webview_flutter", blob) and len(blob) < 40000:
        rep.add(WARN, "The app looks webview-heavy", "source",
                "Thin webview wrappers are rejected under minimum-functionality rules.")


# --------------------------------------------------------------------------- #
# output
# --------------------------------------------------------------------------- #

def render(rep: Report, stacks: list[str], root: Path) -> str:
    order = {BLOCKER: 0, WARN: 1, INFO: 2}
    findings = sorted(rep.findings, key=lambda f: order[f["level"]])
    out = [
        "=" * 72,
        f"  store-ready pre-flight — {root.name}",
        f"  stack: {', '.join(stacks) or 'unknown'}",
        "=" * 72,
        "",
    ]
    if rep.facts:
        out.append("Detected:")
        for k, v in rep.facts.items():
            if isinstance(v, list):
                v = ", ".join(str(x) for x in v) or "(none)"
            out.append(f"  {k:<26} {v}")
        out.append("")

    counts = {lvl: sum(1 for f in findings if f["level"] == lvl) for lvl in (BLOCKER, WARN, INFO)}
    out.append(f"Findings: {counts[BLOCKER]} blocker(s), {counts[WARN]} warning(s), {counts[INFO]} note(s)")
    out.append("")
    for f in findings:
        out.append(f"[{f['level']}] {f['message']}")
        if f["where"]:
            out.append(f"        where: {f['where']}")
        if f["fix"]:
            out.append(f"        fix:   {f['fix']}")
        out.append("")
    out.append("This script reads the repository only. Metadata in App Store Connect")
    out.append("and Play Console must be verified separately — see SKILL.md step 4.")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Pre-submission audit for mobile app projects.")
    ap.add_argument("path", nargs="?", default=".", help="project root")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args()

    root = Path(args.path).expanduser().resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2

    stacks = detect_stack(root)
    if not stacks:
        print(f"error: no recognisable mobile project at {root}", file=sys.stderr)
        print("       expected pubspec.yaml, package.json, *.xcodeproj or settings.gradle", file=sys.stderr)
        return 2

    rep = Report()
    rep.fact("stack", ", ".join(stacks))
    audit_versions(root, rep)
    audit_android(root, rep)
    audit_ios(root, rep)
    audit_secrets(root, rep)
    audit_policy_surface(root, rep)

    if args.json:
        print(json.dumps({"root": str(root), "stacks": stacks,
                          "facts": rep.facts, "findings": rep.findings}, indent=2))
    else:
        print(render(rep, stacks, root))

    return 1 if rep.blockers else 0


if __name__ == "__main__":
    sys.exit(main())
