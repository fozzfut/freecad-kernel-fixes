"""patch_src.py <root>: lane undo-visibility-pe edits on a mirror of fcD/src 2af3f99 (<root>/src/Gui/...).
Property editor: an edit of Visibility / ShowInTree is one undo step (VisibilityTransaction);
tree context 'Toggle Visibility in Tree View' (ShowInTree) is one undo step."""
import sys

root = sys.argv[1]


def edit(path, pairs):
    s = open(path, "rb").read().decode("utf-8")
    crlf = "\r\n" in s
    s = s.replace("\r\n", "\n")
    for a, b in pairs:
        n = s.count(a)
        if n != 1:
            sys.exit("%s: %d matches of %r" % (path, n, a[:80]))
        s = s.replace(a, b)
    if crlf:
        s = s.replace("\n", "\r\n")
    open(path, "wb").write(s.encode("utf-8"))
    print("patched", path)


PI = root + "/src/Gui/propertyeditor/PropertyItem.cpp"
edit(PI, [
("""#include <iomanip>
#include <limits>
""", """#include <iomanip>
#include <limits>
#include <optional>
#include <sstream>
"""),
("""#include <Gui/ViewProviderDocumentObject.h>
#include <Gui/Document.h>
""", """#include <Gui/ViewProviderDocumentObject.h>
#include <Gui/VisibilityTransaction.h>
#include <Gui/Document.h>
"""),
("""constexpr const int highPrec = 16;
}  // namespace
""", """constexpr const int highPrec = 16;

/// Visibility of an object or of its view provider (3D view) and ShowInTree (tree view): the
/// properties whose edit shows or hides an object, as Std_ToggleVisibility, Std_HideSelection or
/// the tree's eye icon do.
bool isShowHideProperty(const App::Property* prop)
{
    App::PropertyContainer* container = prop->getContainer();
    if (auto vp = freecad_cast<Gui::ViewProviderDocumentObject*>(container)) {
        return prop == &vp->Visibility || prop == &vp->ShowInTree;
    }
    if (auto obj = freecad_cast<App::DocumentObject*>(container)) {
        return prop == &obj->Visibility;
    }
    return false;
}

/// False only when assigning the Python literal @a value leaves the boolean @a prop as it is;
/// a value this cannot read counts as a change.
bool assignmentChanges(const App::Property* prop, const std::string& value)
{
    auto boolProp = dynamic_cast<const App::PropertyBool*>(prop);
    if (!boolProp || (value != "True" && value != "False")) {
        return true;
    }
    return boolProp->getValue() != (value == "True");
}

/// The name PropertyEditor::openEditor() gives the transaction of an edit of @a items.
std::string editStepName(const std::vector<App::Property*>& items)
{
    const char* context = "Gui::PropertyEditor::PropertyEditor";
    std::ostringstream str;
    str << QCoreApplication::translate(context, "Edit").toUtf8().constData() << ' ';
    App::PropertyContainer* parent = items.front()->getContainer();
    auto obj = freecad_cast<App::DocumentObject*>(parent);
    if (!obj) {
        if (auto view = freecad_cast<Gui::ViewProviderDocumentObject*>(parent)) {
            obj = view->getObject();
        }
    }
    for (auto prop : items) {
        if (prop->getContainer() != obj) {
            obj = nullptr;
            break;
        }
    }
    if (obj && obj->isAttachedToDocument()) {
        str << obj->getNameInDocument() << '.';
    }
    else {
        str << QCoreApplication::translate(context, "property").toUtf8().constData() << ' ';
    }
    str << items.front()->getName();
    if (items.size() > 1) {
        str << "...";
    }
    return str.str();
}
}  // namespace
"""),
("""    std::ostringstream ss;
    for (auto prop : propertyItems) {
        App::PropertyContainer* parent = prop->getContainer();
        if (!parent || parent->isReadOnly(prop) || prop->testStatus(App::Property::ReadOnly)) {
            continue;
        }

        if (parent->isDerivedFrom<App::Document>()) {
            auto doc = static_cast<App::Document*>(parent);
            ss << "FreeCAD.getDocument('" << doc->getName() << "').";
        }
        else if (parent->isDerivedFrom<App::DocumentObject>()) {
            auto obj = static_cast<App::DocumentObject*>(parent);
            App::Document* doc = obj->getDocument();
            ss << "FreeCAD.getDocument('" << doc->getName() << "').getObject('"
               << obj->getNameInDocument() << "').";
        }
        else if (parent->isDerivedFrom<ViewProviderDocumentObject>()) {
            App::DocumentObject* obj = static_cast<ViewProviderDocumentObject*>(parent)->getObject();
            App::Document* doc = obj->getDocument();
            ss << "FreeCADGui.getDocument('" << doc->getName() << "').getObject('"
               << obj->getNameInDocument() << "').";
        }
        else {
            continue;
        }

        ss << parent->getPropertyPrefix() << prop->getName() << " = " << value << '\\n';
    }

    std::string cmd = ss.str();
    if (cmd.empty()) {
        return;
    }
""", """    std::ostringstream ss;
    // Documents of the objects this assignment really shows or hides (issue 035)
    bool showHide = false;
    std::vector<App::Document*> showHideDocs;
    for (auto prop : propertyItems) {
        App::PropertyContainer* parent = prop->getContainer();
        if (!parent || parent->isReadOnly(prop) || prop->testStatus(App::Property::ReadOnly)) {
            continue;
        }

        App::Document* doc = nullptr;
        if (parent->isDerivedFrom<App::Document>()) {
            doc = static_cast<App::Document*>(parent);
            ss << "FreeCAD.getDocument('" << doc->getName() << "').";
        }
        else if (parent->isDerivedFrom<App::DocumentObject>()) {
            auto obj = static_cast<App::DocumentObject*>(parent);
            doc = obj->getDocument();
            ss << "FreeCAD.getDocument('" << doc->getName() << "').getObject('"
               << obj->getNameInDocument() << "').";
        }
        else if (parent->isDerivedFrom<ViewProviderDocumentObject>()) {
            App::DocumentObject* obj = static_cast<ViewProviderDocumentObject*>(parent)->getObject();
            doc = obj->getDocument();
            ss << "FreeCADGui.getDocument('" << doc->getName() << "').getObject('"
               << obj->getNameInDocument() << "').";
        }
        else {
            continue;
        }

        ss << parent->getPropertyPrefix() << prop->getName() << " = " << value << '\\n';

        if (isShowHideProperty(prop)) {
            showHide = true;
            if (assignmentChanges(prop, value)) {
                showHideDocs.push_back(doc);
            }
        }
    }

    std::string cmd = ss.str();
    if (cmd.empty()) {
        return;
    }

    // Showing or hiding objects here is one undo step, as with the show/hide commands and the
    // tree (VisibilityTransaction: its preference; no step inside an open transaction, during
    // undo/redo, or for an assignment that changes nothing). With PropertyView/AutoTransactionView
    // the editor has already booked its own "Edit ..." transaction, and this books nothing.
    // Other properties keep the editor's own handling.
    std::optional<VisibilityTransaction> showHideStep;
    if (showHide) {
        std::string name = editStepName(propertyItems);
        showHideStep.emplace(name.c_str(), showHideDocs, !showHideDocs.empty());
    }
"""),
])

TR = root + "/src/Gui/Tree.cpp"
edit(TR, [
("""void TreeWidget::onToggleVisibilityInTree()
{
    const auto items = selectedItems();
    for (auto item : items) {
""", """void TreeWidget::onToggleVisibilityInTree()
{
    const auto items = selectedItems();
    // Hiding objects from the tree view (ShowInTree) or showing them again is one undo step
    std::vector<App::Document*> docs;
    for (auto item : items) {
        if (item->type() == ObjectType) {
            auto object = static_cast<DocumentObjectItem*>(item)->object();
            if (object && object->getObject()) {
                docs.push_back(object->getObject()->getDocument());
            }
        }
    }
    VisibilityTransaction transaction(
        QT_TRANSLATE_NOOP("Command", "Toggle Visibility in Tree View"),
        docs,
        !docs.empty()
    );
    for (auto item : items) {
"""),
])
