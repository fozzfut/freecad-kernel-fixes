"""Lane vr6-save: Gui::Document follows every successful App save into the document's own file.
Input: vr6save/src-ctl/Document.cpp (= mig/undo-vis src/Gui/Document.cpp); output: vr6save/src/Document.cpp (CRLF kept).
Each replacement must match exactly once."""
import io, sys
NL = "\n"
text = io.open("C:/dev/occt8-mig/vr6save/src-ctl/Document.cpp", encoding="utf-8", newline="").read()
eol = "\r\n" if "\r\n" in text else "\n"
P = []
P.append(('''    Connection connectSaveDocument;
    Connection connectRestDocument;
''', '''    Connection connectSaveDocument;
    Connection connectFinishSaveDocument;
    Connection connectRestDocument;
'''))
P.append(('''    d->connectSaveDocument = pcDocument->signalSaveDocument.connect(
        std::bind(&Gui::Document::Save, this, sp::_1)
    );
''', '''    d->connectSaveDocument = pcDocument->signalSaveDocument.connect(
        std::bind(&Gui::Document::Save, this, sp::_1)
    );
    // The modified flag lives here, not in App::Document, so every successful save of the
    // document into its own file must reset it, whoever started the save: Std_Save/Std_SaveAs,
    // App.Document.save()/saveAs() from a macro or script, FreeCAD.saveDocument(). The Gui save
    // commands reset it themselves after the save; the App paths never did, so the document
    // stayed "modified" and closing it asked to save unchanged data. App::Document::saveToFile()
    // emits signalFinishSave only after the file is written. saveCopy() writes another file
    // (its name differs from FileName by construction), so the document keeps its flag;
    // recovery snapshots do not emit this signal at all.
    d->connectFinishSaveDocument = pcDocument->signalFinishSave.connect(
        [this](const App::Document& doc, const std::string& filename) {
            if (&doc == d->_pcDocument && filename == doc.FileName.getStrValue()) {
                setModified(false);
            }
        }
    );
'''))
P.append(('''    d->connectSaveDocument.disconnect();
    d->connectRestDocument.disconnect();
''', '''    d->connectSaveDocument.disconnect();
    d->connectFinishSaveDocument.disconnect();
    d->connectRestDocument.disconnect();
'''))
for old, new in P:
    o = old.replace(NL, eol); n = text.count(o)
    if n != 1: sys.exit("%d matches for:\n%s" % (n, old))
    text = text.replace(o, new.replace(NL, eol))
io.open("C:/dev/occt8-mig/vr6save/src/Document.cpp", "w", encoding="utf-8", newline="").write(text)
print("Document.cpp ok", len(P))
