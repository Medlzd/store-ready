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

SECRET_PATTERNS = [
    (r"AIza[0-9A-Za-z_\-]{35}", "Google API key"),
    (r"sk_live_[0-9a-zA-Z]{16,}", "Stripe live secret key"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key id"),
    (r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----", "Private key"),
    (r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*[\"'][^\"'\s]{16,}[\"']", "Hard-coded credential"),
]

SCAN_EXTENSIONS = {".dart", ".kt", ".java", ".swift", ".m", ".mm", ".js", ".jsx", ".ts", ".tsx"}
SKIP_DIRS = {"build", ".git", "node_modules", "Pods", ".dart_tool", "vendor", ".gradle", "DerivedData"}


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

def audit_ios(root: Path, rep: Report) -> None:
    plist = find_file(root, "**/ios/Runner/Info.plist", "**/ios/**/Info.plist", "**/Info.plist")
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
        if len(value) < 15 or value.lower() in {"", "todo", "description"}:
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

    manifests = [p for p in root.glob("**/PrivacyInfo.xcprivacy") if not any(d in p.parts for d in SKIP_DIRS)]
    if manifests:
        rep.fact("privacy_manifest", str(manifests[0].relative_to(root)))
    else:
        rep.add(BLOCKER, "No PrivacyInfo.xcprivacy privacy manifest found", "ios/",
                "Add a privacy manifest declaring data types and required-reason API codes.")


def read_sources(root: Path, limit: int = 1200) -> str:
    chunks, count = [], 0
    for path in root.rglob("*"):
        if count >= limit:
            break
        if path.is_dir() or path.suffix not in SCAN_EXTENSIONS:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
            count += 1
        except OSError:
            continue
    return "\n".join(chunks)


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


def audit_secrets(root: Path, rep: Report) -> None:
    hits = []
    for path in root.rglob("*"):
        if path.is_dir() or path.suffix not in SCAN_EXTENSIONS:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern, label in SECRET_PATTERNS:
            m = re.search(pattern, content)
            if m:
                line = content[: m.start()].count("\n") + 1
                hits.append((label, f"{path.relative_to(root)}:{line}"))
                break
    for label, where in hits[:20]:
        rep.add(BLOCKER, f"Possible {label} committed in source", where,
                "Rotate the credential and move it server-side; binaries are trivially unpacked.")


def audit_policy_surface(root: Path, rep: Report) -> None:
    blob = read_sources(root)
    has_auth = re.search(r"signUp|createUser|registerUser|signInWith|createUserWithEmail", blob) is not None
    has_delete = re.search(r"deleteAccount|delete_account|deleteUser|closeAccount", blob, re.IGNORECASE) is not None
    if has_auth and not has_delete:
        rep.add(BLOCKER, "Account creation found but no account-deletion path detected", "source",
                "Both stores require in-app account deletion plus a public web deletion URL.")
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
