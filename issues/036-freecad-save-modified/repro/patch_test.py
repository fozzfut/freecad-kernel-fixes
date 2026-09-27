"""Lane vr6-save: two class tests appended to Mod/Test/GuiDocument.py (TestGuiDocument).
python patch_test.py <input GuiDocument.py> <output>; CRLF kept."""
import io
import sys

src, dst = sys.argv[1], sys.argv[2]
text = io.open(src, encoding="utf-8", newline="").read()
eol = "\r\n" if "\r\n" in text else "\n"
marker = "    def testAppSaveResetsGuiModified(self):"
if marker in text:
    sys.exit("already patched")
add = '''

    def testAppSaveResetsGuiModified(self):
        # A save into the document's own file leaves the Gui document unmodified, whoever calls it
        # (Std_Save, a macro or a script through App.Document.save()/saveAs()).
        gui_doc = FreeCADGui.getDocument(self.doc.Name)
        with tempfile.TemporaryDirectory() as temp_dir:
            self.doc.addObject("App::FeaturePython", "ModifiedObject")
            self.assertTrue(gui_doc.Modified)
            self.doc.saveAs(os.path.join(temp_dir, "TestDoc.FCStd"))
            self.assertFalse(gui_doc.Modified)

            self.doc.addObject("App::FeaturePython", "ModifiedObject2")
            self.assertTrue(gui_doc.Modified)
            self.doc.save()
            self.assertFalse(gui_doc.Modified)

    def testSaveCopyAndRecoveryKeepGuiModified(self):
        # A copy into another file and a recovery snapshot do not save the document itself.
        gui_doc = FreeCADGui.getDocument(self.doc.Name)
        with tempfile.TemporaryDirectory() as temp_dir:
            self.doc.saveAs(os.path.join(temp_dir, "TestDoc.FCStd"))
            self.doc.addObject("App::FeaturePython", "ModifiedObject")
            self.assertTrue(gui_doc.Modified)

            copy_path = os.path.join(temp_dir, "Copy.FCStd")
            self.doc.saveCopy(copy_path)
            self.assertTrue(os.path.isfile(copy_path))
            self.assertTrue(gui_doc.Modified)

            self.assertTrue(FreeCAD.writeRecoverySnapshotToTransientDir(self.doc))
            self.assertTrue(gui_doc.Modified)
'''
body = text.rstrip("\r\n")
out = body + add.replace("\n", eol)
io.open(dst, "w", encoding="utf-8", newline="").write(out)
print("ok", dst)
