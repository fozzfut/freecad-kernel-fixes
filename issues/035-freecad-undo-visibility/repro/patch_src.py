"""Lane undo-visibility: make every user show/hide action one undo step (Gui::VisibilityTransaction).
Input: src/CommandView.cpp.orig, src/Tree.cpp.orig (git show 3f92900:src/Gui/<name>); output: src/<name> (CRLF kept).
Each replacement must match exactly once."""
import io
import sys

SRC = "C:/dev/occt8-mig/undovis/src/"
NL = "\n"


def patch(name, pairs):
    text = io.open(SRC + name + ".orig", encoding="utf-8", newline="").read()
    eol = "\r\n" if "\r\n" in text else "\n"
    for old, new in pairs:
        o = old.replace(NL, eol)
        n = text.count(o)
        if n != 1:
            sys.exit("%s: %d matches for:\n%s" % (name, n, old))
        text = text.replace(o, new.replace(NL, eol))
    io.open(SRC + name, "w", encoding="utf-8", newline="").write(text)
    print(name, "ok", len(pairs))


CV = []
CV.append(('''#include "ViewProviderGeometryObject.h"
#include "WaitCursor.h"
''', '''#include "ViewProviderGeometryObject.h"
#include "VisibilityTransaction.h"
#include "WaitCursor.h"
'''))
CV.append(('''    ~TransactionView()
    {
        if (document) {
            document->commitCommand();
        }
    }
};
}  // namespace
''', '''    ~TransactionView()
    {
        if (document) {
            document->commitCommand();
        }
    }
};

// Documents a visibility change of the current selection can touch: the selected object's, and
// those of the sub-object and its parent the selection resolves to (a link to another document).
std::vector<App::Document*> selectionDocuments()
{
    std::vector<App::Document*> docs;
    for (const auto& sel : Selection().getCompleteSelection(ResolveMode::NoResolve)) {
        if (!sel.pObject || !sel.pObject->isAttachedToDocument()) {
            continue;
        }
        docs.push_back(sel.pObject->getDocument());
        App::DocumentObject* parent = nullptr;
        std::string element;
        auto obj = sel.pObject->resolve(sel.SubName, &parent, &element);
        if (obj && obj->isAttachedToDocument()) {
            docs.push_back(obj->getDocument());
        }
        if (parent && parent->isAttachedToDocument()) {
            docs.push_back(parent->getDocument());
        }
    }
    return docs;
}

// Whether showing (@a show) or hiding the current selection changes anything (the element
// visibility for a sub-object its parent handles, the view provider's otherwise).
bool selectionChanges(bool show)
{
    for (const auto& sel : Selection().getCompleteSelection(ResolveMode::NoResolve)) {
        if (!sel.pObject || !sel.pObject->isAttachedToDocument()) {
            continue;
        }
        App::DocumentObject* parent = nullptr;
        std::string element;
        auto obj = sel.pObject->resolve(sel.SubName, &parent, &element);
        if (!obj || !obj->isAttachedToDocument()) {
            continue;
        }
        if (parent) {
            int vis = parent->isElementVisible(element.c_str());
            if (vis >= 0) {
                if ((vis > 0) != show) {
                    return true;
                }
                continue;
            }
        }
        auto vp = Application::Instance->getViewProvider(obj);
        if (vp && vp->isShow() != show) {
            return true;
        }
    }
    return false;
}

// Whether showing (@a show) or hiding all objects of the active document changes anything.
bool documentChanges(bool show)
{
    Gui::Document* doc = Application::Instance->activeDocument();
    if (!doc) {
        return false;
    }
    for (auto obj : doc->getDocument()->getObjects()) {
        if (doc->isShow(obj->getNameInDocument()) != show) {
            return true;
        }
    }
    return false;
}

std::vector<App::Document*> activeDocument()
{
    std::vector<App::Document*> docs;
    if (auto doc = App::GetApplication().getActiveDocument()) {
        docs.push_back(doc);
    }
    return docs;
}
}  // namespace
'''))
CV.append(('''void StdCmdToggleVisibility::activated(int iMsg)
{
    Q_UNUSED(iMsg);
    TransactionView transaction(
        getActiveGuiDocument(),
        QT_TRANSLATE_NOOP("Command", "Toggle Visibility")
    );
    Selection().setVisible(SelectionSingleton::VisToggle);
}
''', '''void StdCmdToggleVisibility::activated(int iMsg)
{
    Q_UNUSED(iMsg);
    if (VisibilityTransaction::enabled()) {
        VisibilityTransaction transaction(
            QT_TRANSLATE_NOOP("Command", "Toggle Visibility"),
            selectionDocuments()
        );
        Selection().setVisible(SelectionSingleton::VisToggle);
        return;
    }
    TransactionView transaction(
        getActiveGuiDocument(),
        QT_TRANSLATE_NOOP("Command", "Toggle Visibility")
    );
    Selection().setVisible(SelectionSingleton::VisToggle);
}
'''))
CV.append(('''void StdCmdShowSelection::activated(int iMsg)
{
    Q_UNUSED(iMsg);
    Selection().setVisible(SelectionSingleton::VisShow);
}
''', '''void StdCmdShowSelection::activated(int iMsg)
{
    Q_UNUSED(iMsg);
    VisibilityTransaction transaction(
        QT_TRANSLATE_NOOP("Command", "Show Selection"),
        selectionDocuments(),
        selectionChanges(true)
    );
    Selection().setVisible(SelectionSingleton::VisShow);
}
'''))
CV.append(('''void StdCmdHideSelection::activated(int iMsg)
{
    Q_UNUSED(iMsg);
    Selection().setVisible(SelectionSingleton::VisHide);
}
''', '''void StdCmdHideSelection::activated(int iMsg)
{
    Q_UNUSED(iMsg);
    VisibilityTransaction transaction(
        QT_TRANSLATE_NOOP("Command", "Hide Selection"),
        selectionDocuments(),
        selectionChanges(false)
    );
    Selection().setVisible(SelectionSingleton::VisHide);
}
'''))
TOGGLE_ALL_OLD = '''void StdCmdToggleObjects::activated(int iMsg)
{
    Q_UNUSED(iMsg);
    // go through active document
    Gui::Document* doc = Application::Instance->activeDocument();
    App::Document* app = doc->getDocument();
'''
CV.append((TOGGLE_ALL_OLD, TOGGLE_ALL_OLD.replace('''    Q_UNUSED(iMsg);
''', '''    Q_UNUSED(iMsg);
    VisibilityTransaction transaction(QT_TRANSLATE_NOOP("Command", "Toggle All Objects"), activeDocument());
''')))
for cls, label, show in (("StdCmdShowObjects", "Show All Objects", "true"), ("StdCmdHideObjects", "Hide All Objects", "false")):
    old = '''void %s::activated(int iMsg)
{
    Q_UNUSED(iMsg);
    // go through active document
''' % cls
    CV.append((old, old.replace('''    Q_UNUSED(iMsg);
''', '''    Q_UNUSED(iMsg);
    VisibilityTransaction transaction(
        QT_TRANSLATE_NOOP("Command", "%s"),
        activeDocument(),
        documentChanges(%s)
    );
''' % (label, show))))

TR = []
TR.append(('''#include "ViewProviderDocumentObject.h"
#include "Widgets.h"
''', '''#include "ViewProviderDocumentObject.h"
#include "VisibilityTransaction.h"
#include "Widgets.h"
'''))
TR.append(('''        // Toggle each selected feature's own visibility directly
        for (auto* raw : selectedItems()) {
''', '''        // Toggle each selected feature's own visibility directly, as one undo step
        std::vector<App::Document*> docs;
        for (auto* raw : selectedItems()) {
            if (raw->type() == ObjectType) {
                auto* vp = static_cast<DocumentObjectItem*>(raw)->object();
                if (vp && vp->getObject()) {
                    docs.push_back(vp->getObject()->getDocument());
                }
            }
        }
        VisibilityTransaction transaction(QT_TRANSLATE_NOOP("Command", "Toggle Visibility"), docs);
        for (auto* raw : selectedItems()) {
'''))
TR.append(('''                // Try the ElementVisible API, if that is not supported toggle the Visibility property
                int visible = -1;
                if (parent) {
                    visible = parent->isElementVisible(objname);
                }
                if (parent && visible >= 0) {
                    parent->setElementVisible(objname, !visible);
                }
                else {
                    visible = obj->Visibility.getValue();
                    obj->Visibility.setValue(!visible);
                }
''', '''                // Try the ElementVisible API, if that is not supported toggle the Visibility property
                int visible = -1;
                if (parent) {
                    visible = parent->isElementVisible(objname);
                }
                bool element = parent && visible >= 0;
                if (!element) {
                    visible = obj->Visibility.getValue();
                }
                // one undo step per click
                VisibilityTransaction transaction(
                    visible ? QT_TRANSLATE_NOOP("Command", "Hide")
                            : QT_TRANSLATE_NOOP("Command", "Show"),
                    {obj->getDocument(), parent ? parent->getDocument() : nullptr}
                );
                if (element) {
                    parent->setElementVisible(objname, !visible);
                }
                else {
                    obj->Visibility.setValue(!visible);
                }
'''))

patch("CommandView.cpp", CV)
patch("Tree.cpp", TR)
