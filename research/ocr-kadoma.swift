// Read-only OCR aid for the city's Japanese map images. Every entry still
// requires visual confirmation against the original page before publication.
import Foundation
import ImageIO
import Vision

for filename in CommandLine.arguments.dropFirst() {
    guard let source = CGImageSourceCreateWithURL(URL(fileURLWithPath: filename) as CFURL, nil),
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
        fputs("Cannot read \(filename)\n", stderr)
        continue
    }
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = false
    request.recognitionLanguages = ["ja-JP", "en-US"]
    do {
        try VNImageRequestHandler(cgImage: image).perform([request])
        print("PAGE \(filename)")
        for observation in request.results ?? [] {
            guard let text = observation.topCandidates(1).first?.string else { continue }
            let y = Int((1 - observation.boundingBox.midY) * CGFloat(image.height))
            let x = Int(observation.boundingBox.minX * CGFloat(image.width))
            print(String(format: "%04d,%04d", y, x), text)
        }
    } catch {
        fputs("OCR failed for \(filename): \(error)\n", stderr)
    }
}
