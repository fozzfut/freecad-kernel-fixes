035 - FreeCAD 26.3: Ctrl+Z не возвращает видимость после скрытия тела (owner 27.09.2026)

ЖАЛОБА: «Ctrl+Z не возвращает видимость обратно после того, как я погасил одно тело.»
Воспроизведено (C:/dev/occt8-mig/undovis/runs/base-*): на стоковом 26.3 ни одно действие показа/скрытия не даёт шага
отмены (steps=0), а Ctrl+Z после «Pad -> скрыть тело» отменяет Pad, тело остаётся скрытым.

КОРЕНЬ (weekly 019f5c5):
- src/App/DocumentObject.cpp:83  Visibility.setStatus(Property::NoModify, true)
- src/App/Document.cpp:526       _checkTransaction: What->testStatus(NoModify) -> ignore = true -> транзакция не открывается,
                                 изменение Visibility вне открытой транзакции не записывается.
- src/Gui/CommandView.cpp:117    Std_ToggleVisibility открывает транзакцию только при PropertyView/AutoTransactionView
                                 (по умолчанию false; commit bc9897c, wwmayer); Std_ShowSelection/HideSelection (:1187/:1215),
                                 Std_ShowObjects/HideObjects/ToggleObjects (:1287/:1339/:1381), глаз в дереве
                                 (Tree.cpp:2055-2066) и пробел в дереве (Tree.cpp:1988-2008) не открывают никакой.
  Почему так в апстриме: realthunder сделал изменения ViewProvider записываемыми в транзакцию (TransactionViewProvider) и
  тут же убрал автоименованные транзакции из Command::_invoke «to avoid too many unnecessary transactions»; wwmayer
  вернул транзакцию только для Toggle Visibility/Selectability и только по параметру (документация Std_ToggleVisibility:
  «can only be undone if AutoTransactionView is true»). То есть: отмена видимости выключена ради чистоты стека отмены
  при ПРОГРАММНЫХ изменениях видимости (редактирование эскиза, панели, пересчёт).

ИСПРАВЛЕНИЕ (класс = действия пользователя «показать/скрыть», программные изменения не трогаем):
- новый src/Gui/VisibilityTransaction.h (только заголовок, без экспорта): на каждое действие пользователя - одна
  транзакция на все затронутые документы (один tid), commit в конце действия. Не открывается, если у документа уже есть
  своя (идёт инструмент/панель - изменение входит в его шаг, как раньше), во время undo/redo, при глобальной транзакции и
  если действие ничего не меняет (скрыть скрытое, «скрыть всё» при всём скрытом) - пустых шагов нет.
- подключено: Std_ToggleVisibility («Toggle Visibility»), Std_ShowSelection/HideSelection («Show/Hide Selection»),
  Std_ShowObjects/HideObjects/ToggleObjects («Show/Hide/Toggle All Objects»), глаз в дереве («Hide»/«Show»),
  пробел в дереве («Toggle Visibility»).
- выключатель: BaseApp/Preferences/View/UndoVisibility (по умолчанию true); false = прежнее поведение.
- авто-скрытие предыдущего элемента PartDesign остаётся в транзакции самого элемента (код не менялся; тест C9).
- ветка fcD/src mig/undo-vis 2af3f99 на 3f92900 (= 028+033); патч patches-263/0001 применяется и к 019f5c5.

СБОРКА: portable MSVC 14.44, строки компиляции/линковки bld144 (repro/mkgui.py, 4 исходника заменены).
D0 контроль (те же исходники 3f92900): c8c6750b против поставленного d5b15879 - 28 байт: метки времени PE и строки
__FILE__ двух исходников (путь той же длины) -> конвейер воспроизводит поставку. Исправление 1a135f33.
ABI (repro/abi2.py, сырые таблицы; pefile обрезает длинные списки импорта): экспорты 12230 = weekly, импорт +3
(App::Application::getGlobalTransaction, App::Document::transacting, isTransactionLocked - есть в экспорте weekly
FreeCADApp.dll), -0.

ТЕСТЫ (repro/uvprobe.py, offscreen, 19 случаев; журналы C:/dev/occt8-mig/undovis/runs):
сток 3/19 (все пути FAIL steps=0; проходят только «без изменений»/«внутри инструмента») = отрицательный контроль;
исправление 19/19 (свежие настройки и копия настроек владельца с HybridDesign); UndoVisibility=false -> 3/19, как сток.
TestGuiBase 37 и TestPartDesignGui 21 offscreen: вердикты сток = исправление (у стока свои 1 FAIL + 1 ERROR).
HD smoke_gui 30 тестов без FAIL/ERROR на стоке и на исправлении (консольный фильтр ругается одинаково на обоих: шум
offscreen-платформы и старый ghome-w).

НЕ ПОКРЫТО: правка Visibility в редакторе свойств (вкладка View) - как все свойства вида, по AutoTransactionView
(ЗАКРЫТО патчем 0002, см. раздел 035-PE ниже);
FreeCAD 1.1.1 / «FreeCAD perf» (C:/dev/FreeCAD-perf) - та же ошибка, дерева сборки FreeCADGui 1.1.1 нет.

REVIEW (independent, 27.09.2026): ACCEPTED.
- Re-run of repro/uvprobe.py on the installed delivery (owner cfg copy + HD c492801): 19/19.
- repro/review/rvprobe.py, 22 more cases (offscreen, owner cfg copy + HD; evidence C:/dev/occt8-mig/undovis/review/runs):
  real PartDesign_Pad command + OK, eye, Ctrl+Z x2 (hide, then Pad; sketch shown again); eye during sketch edit
  (own 'Hide' step, chronological before 'Sketch recompute'); datum plane (eye, Space) and sketch (Space) in a body;
  link array element (eye, Hide Selection -> VisibilityList); HD STEP-import dedup structure made by
  hybriddesign.ops.imports.convert (link eye, body eye, link via the root path + Hide Selection, link+body Toggle);
  Assembly WB (owner O-ring copy: component eye, Toggle via the assembly path, Hide All Objects); link to a body of a
  second document (link eye, Hide Selection); face picked -> Hide Selection; feature -> Toggle (PartDesign toggles
  the body); two quick eye clicks = two steps; hide+undo leaves nothing touched; programmatic Visibility/hide()/
  Gui.Selection.setVisible stay out of the undo list (identity).
  Fix 21 PASS + 1 INFO (runs/fix-owner-final); negative control previous DLL d5b15879 1 PASS (R8 identity) + 20 FAIL
  (runs/base-owner; R1 on it = the owner's report: Ctrl+Z removes the Pad, body stays hidden).
- Known gap (INFO R7b): a body of ANOTHER document hidden through a link's child item gets its 'Hide' step in its own
  document; Ctrl+Z in the link's document does not restore it (FreeCAD undo is per document). Stock: not undoable at all.
- Undo names are translated through the "Command" context (MDIView::undoActions); the owner's delivery runs English.

035-PE (lane undo-visibility-pe, 27.09.2026): property editor + "Toggle Visibility in Tree View" - patches-263/0002
CLASS: every USER show/hide path is one undo step. Paths left by 0001: the property editor's Visibility and Show In Tree
checkboxes (View tab; also the object's Visibility in the Data tab when hidden properties are shown) and the tree's
context action "Toggle Visibility in Tree View" (ShowInTree). Without AutoTransactionView they changed the object with
no transaction -> Ctrl+Z skipped them (stock: steps=0; after "hide, then a modeling step" Ctrl+Z undid only the
modeling step and the object stayed hidden).
FIX (fcD/src mig/undo-vis-pe 3eccec5 on 2af3f99): PropertyItem::setPropertyValue books a VisibilityTransaction when the
assigned property is Visibility (object or view provider) or ShowInTree, over the documents of the objects the
assignment really changes; name = the editor's own transaction name ("Edit property Visibility", "..." for several
objects) = what stock shows with AutoTransactionView. Same rules: pref UndoVisibility, joins an open/booked transaction
(task dialog; the editor's own AutoTransactionView/AutoTransactionData "Edit ..." transaction), none during undo/redo or
a global transaction, none without a real change. Other properties untouched. Tree action: one step over the selection.
BUILD: repro/pe/mkgui.py (035 pipeline + PropertyItem.cpp; sources from a git-archive mirror). D0 control (2af3f99)
b0f29fbb vs delivered 1a135f33: 42 bytes = PE timestamps, same-length __FILE__ paths, anonymous-namespace RTTI hash.
Fix 7af65a21; ABI vs delivered: exports 12230 +0 -0, imports +0 -0. Build log 0 warnings.
TESTS (repro/pe/pvprobe.py, 11 cases, offscreen, the value cell clicked with Qt mouse events posted to the editor's
viewport = the user's single click on a checkbox cell; evidence C:/dev/occt8-mig/undovis-pe/runs):
- fix: 11/11 fresh cfg (fix-fresh), owner cfg copy + HD (pv-fix-owner): hide, show, 3-body multi-selection (ONE step
  'Edit property Visibility...'), mixed multi-selection (undo leaves the already hidden one hidden), link + App::Part,
  Show In Tree, tree "Toggle Visibility in Tree View" on 2 objects (one step), other view property Selectable (steps=0 =
  stock), inside an open transaction (joins 'Tool'), inside a real PartDesign_Pad task dialog (no own step, only
  'Make Pad' after OK), chronological order with a modeling step.
- NEGATIVE CONTROL delivered 1a135f33: 3/11 (only the identity cases P8/P9/P10 pass; pv-dlv-fresh).
- UndoVisibility=false: probe lines identical to the delivered DLL (pv-fix-prefoff == pv-dlv-fresh).
- AutoTransactionView=true: fix lines == delivered lines (same names 'Edit property Visibility') except the tree action
  (new step) (pv-dlv-atv vs pv-fix-atv).
- 035 probe uvprobe.py 19/19 on the fix, fresh and owner cfg + HD (uv-fix-fresh, uv-fix-owner).
- TestGuiBase 37 offscreen: per-test verdicts delivered == fix (stock's own 1 FAIL + 1 ERROR); comparator negative
  control (one doctored verdict) caught. RAM <= 0.41 GB per process.
- Exit noise: some offscreen runs end with "Abnormal program termination" after the probe finished (the known offscreen
  "resource deadlock would occur" at close, V3); seen on the delivered DLL and in the 035 lane's stock runs too.
NOT TESTED through the UI: Data-tab Visibility (needs "Show hidden" from the editor's modal context menu).
Observed, unchanged by this patch: after a Show In Tree edit in the property editor the offscreen probe saw the tree row
still shown 0.7 s later (delivered DLL alike); the tree's own action hides it at once. Not investigated.
NOT INSTALLED (lane order). mig/vr6-save (036) and mig/vr6-asm (on 2af3f99) merge cleanly with mig/undo-vis-pe.
