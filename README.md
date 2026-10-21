# Polyglot POCs

A polyglot is one file that is two file types at once, for example a picture that is also a script.
Each folder under `samples-poc-existing/` and `samples-home-baked/` builds one of them.

- `samples-poc-existing/`: harmless rebuilds of tricks seen in real attacks.
- `samples-home-baked/`: combinations built for this project.
- `samples-external/`: polyglots made by other people.

**All payloads are harmless.** They print a line, show a message box or start Calculator.
The one exception is `samples-home-baked/jar-epub/external.zip`, which holds an outside sample (see [JAR + EPUB](#jar--epub)).

## Install everything (Ubuntu)

```
sudo apt install make python3 python3-pil gcc-mingw-w64-x86-64 default-jdk-headless dosfstools
sudo apt install file unzip 7zip wine imagemagick poppler-utils ffmpeg qemu-utils php-cli
make venv
```

The first line is enough to build. The second line is only for the checks.
`make venv` installs two Python packages (pycdlib and pyfatfs) into `.venv/`. The ISO and VHD examples need them.

## Build

```
make            # build and check every example
make build      # only build
make clean      # delete every out/ and work/
make -C samples-poc-existing/bmp-hta     # just one example (same commands)
```

## Every example looks the same

```
input/     the parts, one file each. Put your own files here, with the same names.
out/       the result
scripts/   the build and check scripts
src/       source code of the demo parts, if they are compiled
```

`make inputs` in an example recreates its demo parts in `input/` (for example by compiling `src/`).
`make verify` checks the result against the demo parts; with your own parts, `make build` is enough.

If Docker and the `am-lab-remnux` image are installed, some checks also run in that container. Otherwise they are skipped.

## The examples

| Example | One file that is… | Based on |
|---|---|---|
| [ZIP + ZIP](#zip--zip) | two ZIP archives: 7-Zip shows one, Explorer and `unzip` the other | Perception Point, Nov 2024 |
| [MSI + JAR](#msi--jar) | a signed installer and a Java program | GlueBall, CVE-2020-1464 |
| [PDF + MHT](#pdf--mht) | a PDF and a Word document with a macro | "MalDoc in PDF", JPCERT/CC, Aug 2023 |
| [EXE + HTA](#exe--hta) | a Windows program and an HTA script | Emmenhtal 2024, ClickFix / Lumma 2024–25 |
| [BMP + HTA](#bmp--hta) | a picture and an HTA script | Lazarus, Apr 2021 |
| [HTML + DLL](#html--dll) | a web page and a Windows DLL | StrelaStealer, 2022–24 |
| [GIF + PHP](#gif--php) | a picture and a PHP script | AhnLab ASEC, Dec 2020 |
| [EXE + ZIP](#exe--zip) | a Windows program and a ZIP archive | home-baked |
| [JPEG + ISO](#jpeg--iso) | a picture and a disk image Windows mounts | home-baked |
| [JPEG + VHD](#jpeg--vhd) | a picture and a virtual disk Windows mounts | home-baked |
| [MP3 + DOCM](#mp3--docm) | an audio file and a Word document with a macro | home-baked |
| [JAR + EPUB](#jar--epub) | a Java program and an ebook | home-baked |

The "Rules" lines below matter only when you put your own files into `input/`.

### ZIP + ZIP
`samples-poc-existing/zip-concat` → `out/SHIPPING_INV_PL_BL_pdf.zip`

- Input: `decoy.zip` (the first ZIP, a real one-page PDF) and `payload.zip` (the second ZIP, a `.bat` that only prints a message).
- Try it: `7z l out/SHIPPING_INV_PL_BL_pdf.zip`, then `unzip -l out/SHIPPING_INV_PL_BL_pdf.zip`. They list different files.
  On Windows 10, Explorer shows the `.bat` (as `SHIPPING_INV_PL_BL.pdf` with extensions hidden).
- Why: 7-Zip reads from the start and stops at the first archive (it warns "There are data after the end of archive").
  Explorer, WinRAR, `unzip` and Python find the end record from the end of the file and land in the second ZIP.
  A plain `cat`/`copy /b` works for 7-Zip and `unzip`, but Explorer rejects it, so `scripts/concat.py` shifts the second ZIP's two offset fields by the size of the first.
- Rules: any two normal ZIP files; ZIP64 (over 4 GB) does not work.
- Reading: [BleepingComputer on Perception Point's report](https://www.bleepingcomputer.com/news/security/hackers-now-use-zip-file-concatenation-to-evade-detection/), [ZipDiff](https://github.com/ouuan/ZipDiff), [CVE-2025-54368 (uv)](https://astral.sh/blog/uv-security-advisory-cve-2025-54368).

### MSI + JAR
`samples-poc-existing/msi-jar-signature` → `out/polyglot.msi` (or `out/demo.jar` when there is no MSI)

- Input: `installer.msi` (not included: put your own **signed** MSI here) and `program.jar`.
- Try it: `java -jar out/polyglot.msi` shows a message box. On Windows without the August 2020 fix, the file properties still show a valid signature.
- Why: the build is a plain append (`copy /b signed.msi + program.jar`). Windows read the MSI and its signature from the start; Java reads the JAR from the end.
- Rules: the JAR needs a `Main-Class` line in its manifest.
- Reading: [VirusTotal, Jan 2019](https://blog.virustotal.com/2019/01/distribution-of-malicious-jar-appended.html), [NVD CVE-2020-1464](https://nvd.nist.gov/vuln/detail/CVE-2020-1464).

### PDF + MHT
`samples-poc-existing/pdf-mht` → `out/invoice.pdf`

- Input: `document.pdf` and `document.mht` (a Word document saved as a web archive, with its macro).
- Try it: open `out/invoice.pdf` in a PDF reader: one page. Copy it to `invoice.doc` and open it in Word on Windows: with macros enabled, the macro shows a message box.
- Why: the MHT is appended after the PDF. PDF readers stop at the PDF; Word picks its converter by sniffing the content and finds the MHT.
  `pdfid -e` sees a clean PDF; `olevba` only finds the macro after the MHT part is carved out.
- Rules: any PDF and any MHT work.
- Reading: [JPCERT/CC "MalDoc in PDF"](https://blogs.jpcert.or.jp/en/2023/08/maldocinpdf.html), [Didier Stevens' analysis](https://blog.didierstevens.com/2023/08/29/quickpost-analysis-of-pdf-activemime-polyglot-maldocs/).

### EXE + HTA
`samples-poc-existing/pe-hta` → `out/polyglot.exe`

- Input: `program.exe` and `script.hta`.
- Try it: double-click `polyglot.exe` on Windows (or `wine out/polyglot.exe`): the program runs. `mshta "C:\full\path\polyglot.exe"`: the script shows a message box.
- Why: the build writes `<!--` into DOS-header bytes the Windows loader ignores and appends `-->` plus the script, so an HTML parser sees one comment and then a `<script>`. `mshta` ignores the extension and the magic bytes.
  The ZLoader variant (2022) hides the script inside the Authenticode signature instead; that needs a signed binary and is not re-created here.
- Rules: the EXE must not contain `-->` or `--!>` (the build stops and tells you).
- Reading: [Qualys on Lumma's crafted Dialer.exe, Oct 2024](https://blog.qualys.com/vulnerabilities-threat-research/2024/10/20/unmasking-lumma-stealer-analyzing-deceptive-tactics-with-fake-captcha), [Orange Cyberdefense on Emmenhtal](https://www.orangecyberdefense.com/global/blog/cert-news/emmenhtal-loader-a-cybersecurity-threat-distributing), [Check Point on ZLoader](https://research.checkpoint.com/2022/can-you-trust-a-files-digital-signature-new-zloader-campaign-exploits-microsofts-signature-verification-putting-users-at-risk/).

### BMP + HTA
`samples-poc-existing/bmp-hta` → `out/polyglot.bmp`

- Input: `image.bmp` and `script.hta`.
- Try it: open `out/polyglot.bmp` in an image viewer: the picture. On Windows, copy it to `polyglot.hta` and double-click: the script shows a message box.
  (`mshta polyglot.bmp` only shows the picture: MSHTML sniffs the `BM` magic and renders an image.)
- Why: `<!--` goes into the two reserved BMP header fields and `--><script>…</script>` after the pixels; image readers ignore both.
- Rules: the BMP must not contain `-->` or `--!>` (the build stops and tells you).
- Reading: [Malwarebytes on Lazarus, Apr 2021](https://www.malwarebytes.com/blog/threat-intelligence/2021/04/lazarus-apt-conceals-malicious-code-within-bmp-file-to-drop-its-rat), [MITRE ATT&CK T1218.005](https://attack.mitre.org/techniques/T1218/005/).

### HTML + DLL
`samples-poc-existing/html-dll` → `out/polyglot.html`

- Input: `payload.dll` (64-bit) and `page.html`.
- Try it: open `out/polyglot.html` in a browser: the page. On Windows `rundll32 polyglot.html,Run` (or `wine rundll32 out/polyglot.html,Run`): the DLL shows a message box.
- Why: the DLL starts with `MZ`, the HTML parser shows that as text and swallows the rest of the DLL in a comment; `rundll32` only needs a valid PE.
- Rules: the DLL must not contain `-->` or `--!>`; `Run` is the demo DLL's export, use your own function's name.
- Reading: [DCSO CyTec, Nov 2022](https://medium.com/@DCSO_CyTec/shortandmalicious-strelastealer-aims-for-mail-credentials-a4c3e78c8abc), [Unit 42 on StrelaStealer](https://unit42.paloaltonetworks.com/strelastealer-campaign/).

### GIF + PHP
`samples-poc-existing/image-php` → `out/avatar.gif`

- Input: `image.gif` and `script.php`.
- Try it: open `out/avatar.gif` in an image viewer: the picture. `php out/avatar.gif`: PHP prints the picture bytes, then runs the code (the demo code also tries to start `calc.exe`).
  Without a local PHP: `docker run --rm -v "$PWD/out:/w:ro" php:cli php /w/avatar.gif`.
- Why: the PHP sits in a GIF comment. Every image tool decodes the picture (metadata tools even show the PHP, as a comment); PHP outputs everything outside `<?php ?>` and runs the code.
- Rules: `<?` may appear only once, at the start of your PHP code (the build stops otherwise); GIF87a and GIF89a both work.
- Reading: [AhnLab ASEC](https://asec.ahnlab.com/en/18861/).

### EXE + ZIP
`samples-home-baked/exe-zip` → `out/polyglot.exe`

- Input: `program.exe` and the folder `zip/` (the files that go into the ZIP; add or remove freely).
- Try it: `wine out/polyglot.exe` prints `hello from polyglot`; `unzip -l out/polyglot.exe` lists the files from `input/zip/`. Renamed to `.zip`, Explorer opens it too.
- Why: the ZIP is the PE's overlay, which the loader never reads. The ZIP is written with absolute offsets, like a self-extracting archive, so even Explorer accepts it.
- Rules: any Windows EXE works; a signed EXE loses its valid signature.

### JPEG + ISO
`samples-home-baked/image-iso` → `out/polyglot.iso`

- Input: `cover.jpg` and `payload.lnk` (the demo is a shortcut that opens Calculator).
- Try it: copy it to `polyglot.jpg` and open it: the picture. On Windows, double-click `polyglot.iso`: a drive opens with `payload.lnk` in it.
- Why: ISO 9660 leaves its first 32 KiB unused, so the JPEG lives there; Windows mounts the ISO from offset 0x8000.
  Malware moved to ISO delivery in 2022 partly because mounted contents did not inherit Mark-of-the-Web; Windows 11 22H2+ now propagates it.
- Rules: the picture must be 32 KB (32768 bytes) or smaller; the file inside is always named `payload.lnk`.

### JPEG + VHD
`samples-home-baked/image-vhd` → `out/polyglot.vhd`

- Input: `cover.jpg` and `payload.lnk` (the demo is a shortcut that opens Calculator).
- Try it: `file out/polyglot.vhd` says JPEG image. On Windows, double-click `polyglot.vhd`: a drive opens with `payload.lnk` in it.
- Why: the JPEG fills the disk's boot code area, which is never read during a mount; Windows finds the VHD from its footer in the last 512 bytes.
- Rules: the picture must be 446 bytes or smaller (it has to fit before the partition table); the file name on the disk is your file's name in `input/`.

### MP3 + DOCM
`samples-home-baked/mp3-docm` → `out/polyglot.mp3` and `out/polyglot.docm` (the same bytes)

- Input: `audio.mp3` and `document.docm` (a Word document with a macro).
- Try it: `file out/polyglot.mp3` says audio (`ffprobe` reads 4 seconds of it). Open `polyglot.docm` in Microsoft Word: the macro document (LibreOffice refuses it).
- Why: the file starts with the MP3's ID3 tag and audio frames; the DOCM is a ZIP, found from the end, and Word opens Office ZIPs with a stub in front.
  Tools that route files by their first bytes send it to an audio branch, and audio is rarely scanned in depth.
- Rules: the MP3 should start with an ID3 tag and the document should contain a macro (`word/vbaProject.bin`); the build warns otherwise.

### JAR + EPUB
`samples-home-baked/jar-epub` → `out/hertz.epub` (and `out/Philipp.Schott.epub`, see below)

- Input: `program.jar` and `book.epub`.
- Try it: open `out/hertz.epub` in an ebook reader: the book. Copy it to `hertz.jar` and run `java -jar hertz.jar`: Java shows a message box.
- Why: both formats are ZIP archives, so the build merges the two into one archive that keeps the EPUB rules (`mimetype` stored first) and the JAR manifest.
- Rules: the JAR needs a `Main-Class` line in its manifest; if both contain the same file name, the JAR's copy is kept.
- **Outside sample:** `external.zip` (password `infected`) holds a JAR from elsewhere, named by its SHA-256, plus an ebook.
  The build unpacks it into `external/` automatically and builds `out/Philipp.Schott.epub` from it.
  The JAR looks like real malware: **never run it or `out/Philipp.Schott.epub`**. The build and the checks only read it.

## Further reading

- Ange Albertini: [Funky File Formats](https://github.com/corkami/pocs) and [Mitra](https://github.com/corkami/mitra).
- Koch et al., ["On the Abuse and Detection of Polyglot Files"](https://arxiv.org/abs/2407.01529) (2024).
