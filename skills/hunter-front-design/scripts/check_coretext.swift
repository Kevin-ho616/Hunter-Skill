// Process-scoped registration and actual CTLine shaping; does not install a system font.
import Foundation
import CoreText
import CryptoKit

guard CommandLine.arguments.count >= 3 else {
    fatalError("Usage: swift check_coretext.swift /absolute/font.ttf 'sample text' [language]")
}
let url = URL(fileURLWithPath: CommandLine.arguments[1]).standardizedFileURL
guard FileManager.default.fileExists(atPath: url.path) else { fatalError("Font does not exist") }
var error: Unmanaged<CFError>?
guard CTFontManagerRegisterFontsForURL(url as CFURL, .process, &error) else {
    fatalError("Registration failed: \(String(describing: error?.takeRetainedValue()))")
}
defer { CTFontManagerUnregisterFontsForURL(url as CFURL, .process, nil) }
guard let descriptors = CTFontManagerCreateFontDescriptorsFromURL(url as CFURL) as? [CTFontDescriptor],
      let descriptor = descriptors.first else { fatalError("No font descriptor") }
let sourceFont = CTFontCreateWithFontDescriptor(descriptor, 48, nil)
let name = CTFontCopyPostScriptName(sourceFont) as String
let font = CTFontCreateWithName(name as CFString, 48, nil)
guard CTFontCopyPostScriptName(font) as String == name,
      let loadedURL = CTFontCopyAttribute(font, kCTFontURLAttribute) as? URL,
      loadedURL.standardizedFileURL == url else { fatalError("Registered font resolves to another file") }
let text = CommandLine.arguments[2]
var attrs: [NSAttributedString.Key: Any] = [NSAttributedString.Key(kCTFontAttributeName as String): font]
if CommandLine.arguments.count > 3 { attrs[NSAttributedString.Key(kCTLanguageAttributeName as String)] = CommandLine.arguments[3] }
let line = CTLineCreateWithAttributedString(NSAttributedString(string: text, attributes: attrs))
let runs = CTLineGetGlyphRuns(line) as! [CTRun]
var output: [[String: Any]] = []
for run in runs {
    let count = CTRunGetGlyphCount(run)
    var glyphs = [CGGlyph](repeating: 0, count: count)
    var positions = [CGPoint](repeating: .zero, count: count)
    CTRunGetGlyphs(run, CFRange(location: 0, length: 0), &glyphs)
    CTRunGetPositions(run, CFRange(location: 0, length: 0), &positions)
    let runAttributes = CTRunGetAttributes(run) as NSDictionary
    let runFont = runAttributes[kCTFontAttributeName] as! CTFont
    guard !glyphs.contains(0), CTFontCopyPostScriptName(runFont) as String == name else {
        fatalError("Missing glyph or unexpected font fallback")
    }
    output.append(["glyphs": glyphs.map { Int($0) }, "positions": positions.map { [$0.x, $0.y] }])
}
guard !output.isEmpty else { fatalError("No shaped runs") }
let report: [String: Any] = ["status": "pass", "font": url.path, "postscript": name, "text": text,
    "sha256": SHA256.hash(data: try Data(contentsOf: url)).map { String(format: "%02x", $0) }.joined(),
    "runs": output, "scope": "macOS CoreText process registration and shaping; no system installation or application proof"]
print(String(data: try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]), encoding: .utf8)!)
