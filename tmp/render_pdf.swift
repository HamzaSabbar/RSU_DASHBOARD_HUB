import AppKit
import Foundation
import PDFKit

let args = CommandLine.arguments
guard args.count >= 3 else {
    fputs("usage: render_pdf.swift <pdf> <output-dir>\n", stderr)
    exit(2)
}

let pdfURL = URL(fileURLWithPath: args[1])
let outputURL = URL(fileURLWithPath: args[2], isDirectory: true)
try FileManager.default.createDirectory(at: outputURL, withIntermediateDirectories: true)

guard let document = PDFDocument(url: pdfURL) else {
    fputs("could not open PDF\n", stderr)
    exit(1)
}

print("PAGES \(document.pageCount)")

for pageIndex in 0..<document.pageCount {
    guard let page = document.page(at: pageIndex) else { continue }

    print("----- PAGE \(pageIndex + 1) TEXT -----")
    if let text = page.string, !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
        print(text)
    }

    let bounds = page.bounds(for: .mediaBox)
    let targetSize = NSSize(width: bounds.width * 2.0, height: bounds.height * 2.0)
    let image = page.thumbnail(of: targetSize, for: .mediaBox)
    guard
        let tiff = image.tiffRepresentation,
        let rep = NSBitmapImageRep(data: tiff),
        let png = rep.representation(using: .png, properties: [:])
    else {
        fputs("could not render page \(pageIndex + 1)\n", stderr)
        continue
    }

    let pageName = String(format: "page-%02d.png", pageIndex + 1)
    try png.write(to: outputURL.appendingPathComponent(pageName))
}
