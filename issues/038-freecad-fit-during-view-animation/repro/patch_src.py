"""Lane vr6-unconf: sources of the two fixes (each replacement must match exactly once; EOL of the file kept).
Inputs: src-gui/<name>.orig (git show mig/undo-vis:src/Gui/...), src-part/<name>.orig (git show mig/G:src/Mod/Part/Gui/...).
Outputs: src-gui/<name>, src-part/<name>.
  036 FreeCADGui: a camera fit (fit all / fit selection / bound box) issued while a finite navigation animation
      still runs first brings that animation to its end (the running animation would otherwise keep rotating the
      camera about its old rotation centre after the fit).
  037 PartGui: SoBrepFaceSet::getBoundingBox counts only the faces of a secondary selection context again
      (fit selection of a face; lost upstream in ebf13e20e together with the legacy OpenGL code)."""
import io
import sys

ROOT = "C:/dev/occt8-mig/vr6unconf/"
NL = "\n"


def patch(sub, name, pairs):
    text = io.open(ROOT + sub + "/" + name + ".orig", encoding="utf-8", newline="").read()
    eol = "\r\n" if "\r\n" in text else "\n"
    for old, new in pairs:
        o = old.replace(NL, eol)
        n = text.count(o)
        if n != 1:
            sys.exit("%s: %d matches for:\n%s" % (name, n, old))
        text = text.replace(o, new.replace(NL, eol))
    io.open(ROOT + sub + "/" + name, "w", encoding="utf-8", newline="").write(text)
    print(sub, name, "ok", len(pairs))


# ------------------------------------------------------------------ 036 FreeCADGui
patch("src-gui", "NavigationAnimator.h", [(
'''    void stop();
    bool isAnimating() const;
''', '''    void stop();
    void finish();
    bool isAnimating() const;
''')])

patch("src-gui", "NavigationAnimator.cpp", [(
'''/**
 * @return Whether or not an animation is active
 */''', '''/**
 * @brief Brings a running finite animation to its end state at once, as if its time had run out
 *
 * The last update and onStop(true) run as at a normal end (exact target pose, finished and
 * completed signals). An infinite animation (spinning) has no end state and keeps running.
 */
void NavigationAnimator::finish()
{
    if (!activeAnimation || activeAnimation->state() != QAbstractAnimation::State::Running) {
        return;
    }
    if (activeAnimation->loopCount() < 0 || activeAnimation->totalDuration() < 0) {
        return;
    }
    // Reaching the end emits finished(), whose handler resets activeAnimation: keep the object alive
    const std::shared_ptr<NavigationAnimation> animation = activeAnimation;
    animation->setCurrentTime(animation->totalDuration());
}

/**
 * @return Whether or not an animation is active
 */''')])

patch("src-gui", "NavigationStyle.h", [(
'''    void stopAnimating() const;
''', '''    void stopAnimating() const;
    void finishAnimating() const;
''')])

patch("src-gui", "NavigationStyle.cpp", [(
'''void NavigationStyle::stopAnimating() const
{
    animator->stop();
}
''', '''void NavigationStyle::stopAnimating() const
{
    animator->stop();
}

/**
 * @brief Brings a running camera animation (view orientation, translation) to its end pose at once
 *
 * For callers that place the camera absolutely from its current pose (fit all, fit selection):
 * a FixedTimeAnimation left running rotates the camera about its own rotation centre after the new
 * placement and moves the fitted view away. Spinning is left running.
 */
void NavigationStyle::finishAnimating() const
{
    animator->finish();
}
''')])

FIN = '''    // A view animation still running (e.g. Right view pressed just before) would keep turning the
    // camera about its old rotation centre after this fit: bring it to its end pose first.
    navigation->finishAnimating();

'''
patch("src-gui", "View3DInventorViewer.cpp", [
    ('''void View3DInventorViewer::viewAll()
{
''', '''void View3DInventorViewer::viewAll()
{
''' + FIN),
    ('''void View3DInventorViewer::viewObjects(const std::vector<App::SubObjectT>& objs, bool extend)
{
    if (!guiDocument) {
        return;
    }
''', '''void View3DInventorViewer::viewObjects(const std::vector<App::SubObjectT>& objs, bool extend)
{
    if (!guiDocument) {
        return;
    }

''' + FIN.rstrip("\n") + "\n"),
    ('''            box.setBounds(minx, miny, minz, maxx, maxy, maxz);
        }
        viewBoundBox(box);
    }
}
''', '''            box.setBounds(minx, miny, minz, maxx, maxy, maxz);
        }
        else {
            // A selection without extent (one vertex, points that coincide) gives no size to fit:
            // centre it at the current zoom instead of setting a camera of zero height.
            SbSphere sphere;
            sphere.circumscribe(box);
            if (sphere.getRadius() == 0.0F) {
                navigation->translateCamera(box.getCenter() - getFocalPoint());
                return;
            }
        }
        viewBoundBox(box);
    }
}
'''),
    ('''void View3DInventorViewer::viewBoundBox(const SbBox3f& box)
{
''', '''void View3DInventorViewer::viewBoundBox(const SbBox3f& box)
{
''' + FIN),
])

# ------------------------------------------------------------------ 037 PartGui
patch("src-part", "SoBrepFaceSet.cpp", [
    ('''void SoBrepFaceSet::getBoundingBox(SoGetBoundingBoxAction* action)
{
    inherited::getBoundingBox(action);
}
''', '''// Extends `box` by the vertices of the topological faces in `parts`. partIndex holds the triangle
// count of each face; each triangle's indices in coordIndex end with -1 (walked like
// buildOverlayCoordIndex, so stray delimiters are tolerated). Indices outside the points are skipped.
static void extendByParts(
    SbBox3f& box,
    const SbVec3f* points,
    const SoCoordinateElement* coords,
    int pointCount,
    const int32_t* coordIndex,
    int coordIndexCount,
    const int32_t* partTriCounts,
    int partCount,
    const std::set<int>& parts
)
{
    if (!coordIndex || coordIndexCount <= 0 || !partTriCounts || partCount <= 0 || parts.empty()) {
        return;
    }
    const int lastPart = *parts.rbegin();
    int pos = 0;
    for (int part = 0; part < partCount && part <= lastPart && pos < coordIndexCount; ++part) {
        const bool include = (parts.find(part) != parts.end());
        const int tris = partTriCounts[part];
        for (int t = 0; t < tris && pos < coordIndexCount; ++t) {
            while (pos < coordIndexCount && coordIndex[pos] < 0) {
                pos++;
            }
            while (pos < coordIndexCount && coordIndex[pos] >= 0) {
                const int idx = coordIndex[pos++];
                if (include && idx < pointCount) {
                    box.extendBy(points ? points[idx] : coords->get3(idx));
                }
            }
            if (pos < coordIndexCount && coordIndex[pos] < 0) {
                pos++;
            }
        }
    }
}

void SoBrepFaceSet::getBoundingBox(SoGetBoundingBoxAction* action)
{
    // A secondary selection context names the faces that count, e.g. the picked face that
    // ViewProvider::getBoundingBox marks for Std_ViewFitSelection, or the shown faces of a partly
    // rendered link. Without one, or with all faces, the box is the whole face set (as before).
    // SoBrepEdgeSet and SoBrepPointSet do the same for their elements.
    SelContextPtr ctx2 = Gui::SoFCSelectionRoot::getSecondaryActionContext<SelContext>(action, this);
    if (!ctx2 || ctx2->isSelectAll()) {
        inherited::getBoundingBox(action);
        return;
    }
    if (ctx2->selectionIndex.empty()) {
        return;
    }

    const SbVec3f* points = nullptr;
    const SoCoordinateElement* coords = nullptr;
    int pointCount = 0;
    auto* vertexProp = static_cast<SoVertexProperty*>(this->vertexProperty.getValue());
    if (vertexProp && vertexProp->vertex.getNum() > 0) {
        points = vertexProp->vertex.getValues(0);
        pointCount = vertexProp->vertex.getNum();
    }
    else {
        coords = SoCoordinateElement::getInstance(action->getState());
        pointCount = coords->getNum();
    }

    SbBox3f bbox;
    extendByParts(
        bbox,
        points,
        coords,
        pointCount,
        this->coordIndex.getValues(0),
        this->coordIndex.getNum(),
        this->partIndex.getValues(0),
        this->partIndex.getNum(),
        ctx2->selectionIndex
    );
    if (!bbox.isEmpty()) {
        action->extendBy(bbox);
    }
}
'''),
])
