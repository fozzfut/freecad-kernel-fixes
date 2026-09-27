040 - FreeCAD 26.3: при загруженном HybridDesign ломается верстак Assembly (STUMBLES.md 27.09, баг 1)

СИМПТОМ: Assembly_InsertLink не открывает панель; в отчёте трейсбеки InitGui.py shouldShow ->
UtilsAssembly.activeAssembly: 'Gui.ViewProviderGeometryObject' object has no attribute 'isInEditMode'.
У объекта сборки ViewObject.TypeId = AssemblyGui::ViewProviderAssembly, а Python-обёртка базовая.

КОРЕНЬ (weekly 019f5c5; не в HD и не в наших патчах):
- src/Gui/ViewProviderGeometryObject.cpp:91  конструктор делает Selectable.setValue(...) -> ViewProvider::onChanged
  (src/Gui/ViewProvider.cpp:607) -> Gui::Application::signalChangedObject (и onBeforeChange -> signalBeforeChangeObject).
- src/Gui/DocumentObserverPython.cpp:202/:222  slotBeforeChangeObject/slotChangedObject сразу зовут Obj.getPyObject().
  Объект ещё строится (работает конструктор базового класса), виртуальный вызов уходит в
  ViewProviderGeometryObject::getPyObject (:419) -> создаётся ViewProviderGeometryObjectPy и кэшируется в pyViewObject
  на всю жизнь объекта. Производный getPyObject (ViewProviderAssembly.cpp:1461 и ещё 10 классов) уже не вызывается.
- Попутно Obj.getPropertyName() сливает таблицу свойств строящегося класса (PropertyData parentMerged), и конструктор,
  который после этого добавляет свойство, падает: Fem::FemMeshObject не создаётся ("Cannot add static property",
  src/App/PropertyContainer.cpp:469).
- Триггер - ЛЮБОЙ Python-наблюдатель Gui (Gui.addDocumentObserver) со slotChangedObject или slotBeforeChangeObject.
  Пустой наблюдатель без HD даёт ровно то же, что HD (vr6asm/runs/base-obs = base-hd). HD регистрирует несколько таких
  (render_cache, progressive, through_mesh, open_progress ...) - это их штатная работа, убрать их = убрать функции.
- Почему Assembly только на 26.3: в 26.3 Gui::ViewProviderPart наследует ViewProviderGeometryObject; в 1.1.1 - нет,
  там сборка цела, но Part/PartDesign/Sketcher/Mesh/FEM ломаются так же (vr6asm/runs/o111-obs).

КЛАСС (условие): объект Gui-вьюпровайдера отдан в Python, пока он не достроен. Члены класса, измерено
(vpprobe.py, 28 типов, создание + сохранение/открытие): с наблюдателем на поставке 11 типов с неверной обёрткой
(Assembly, Part::Box/Feature/FeaturePython/Part2DObjectPython, Sketch, Body, PD Pad/FeatureBase, Surface::Filling,
Mesh, Fem::ConstraintFixed) + FemMesh не создаётся; без наблюдателя - всё верно.

ИСПРАВЛЕНИЕ (одно место - шлюз в Python): DocumentObserverPython::slotBeforeChangeObject/slotChangedObject не
вызывают Python для вьюпровайдера документа, ещё не прикреплённого к объекту (getObject() == nullptr). Прикрепление
(Gui::Document::slotNewObject: createInstance() -> attach()) - наблюдаемый конец конструирования. Изменения свойств
по умолчанию внутри конструктора Python-наблюдатели больше не видят (заявленное изменение); все события после
attach - как в стоке. C++-подписчики сигналов не тронуты.
ЗАЯВЛЕННОЕ ИЗМЕНЕНИЕ точно (ревью r1, m1): Python-наблюдатели не получают изменения свойств, сделанные ДО того, как
ViewProviderDocumentObject::attach установил объект: (1) значения по умолчанию из конструкторов; (2) часть
производного attach(), которая выполняется до вызова базового attach(). Из 52 переопределений attach() у
вьюпровайдеров такая часть есть только у ViewProviderSubShapeBinder::attach (src/Mod/PartDesign/Gui/
ViewProviderShapeBinder.cpp:249-256: UseBinderStyle.setValue и его каскад onChanged - ShapeAppearance, LineColor,
LineColorArray, PointColor, PointColorArray, PointMaterial, Transparency, LineWidth; 12 событий UseBinderStyle в
review-r1/runs/rv-dlv-obs). Сток отдавал их Python с Object == None; вреда нет, но это часть изменения. Почему не иначе: переделка каждого из 11 getPyObject
лечит известные классы, не класс ошибок; пересоздание обёртки после attach ломает ссылки, уже отданные в Python, и
требует нового члена ViewProvider (ABI всех модулей).
Ветка fcD/src mig/vr6-asm 01c0dbd на mig/undo-vis 2af3f99 (= 17b81be с уточнённым сообщением, дерево то же, DLL та же;
17b81be сохранён как backup/vr6-asm-r1); patches-263/0001 применяется и к 019f5c5 (файл не менялся).

СБОРКА: portable MSVC 14.44, строки bld144 (repro/mkgui.py, 5 исходников: 4 из 033/035 + DocumentObserverPython.cpp).
D0 контроль (исходники 2af3f99 по пути той же длины): 32e01a59 против поставленного 1a135f33 - 37 байт: метки времени
PE и строки __FILE__. Исправление 6a83a9c1. ABI против контроля: экспорты 12230 +0/-0, импорт 8426 +0/-0.

ТЕСТЫ (C:/dev/occt8-mig/vr6asm/runs; offscreen, <= 450 МБ на процесс):
- vpprobe (Std_New/addObject, save+open, Assembly_CreateAssembly -> activeAssembly -> Assembly_InsertLink):
  поставка+HD / поставка+пустой наблюдатель: 11 из 28 типов неверны, activeAssembly AttributeError, панели нет;
  исправление: без HD, с пустым наблюдателем, с HD master c492801 (урезанный конфиг владельца и полный) - 28/28 = без
  HD (создание и открытие), activeAssembly = сборка, панель InsertLink открыта.
- Поток событий наблюдателя: сток 812 событий у недостроенных объектов -> 0; события прикреплённых объектов совпадают
  (разница только Assembly - на стоке его путь ломался - и FemMesh, который на стоке не создавался).
- FreeCAD сток против исправления: Document (135, вкл. testGuiObserver) - тесты и вердикты те же, сообщения = шум двух
  стоковых прогонов (UUID, Part1/Part2); TestGuiBase 37 SAME (стоковые 1 FAIL + 1 ERROR); TestAssemblyWorkbench 35
  SAME (стоковые 2 ERROR '_Move'.Label); TestPartDesignGui 21 SAME (шум offscreen). Первый прогон TestGuiBase на
  исправлении завис в рендер-тесте TestCoinNodeSnapshots (offscreen GL, машина загружена), повтор - SAME.
- HD tests/gui/vp_wrappers_gui.py (ветка HD fix/vr6-asm): исправление 4/4 OK; поставка - 3 skip (нет 040);
  HD_VPW_STRICT=1 на поставке - 3 FAIL (отрицательный контроль: 11 типов, 'ViewProviderGeometryObject' != Assembly).
  HD smoke_gui 30/30, subassembly_gui 24/24, ribbon_gui 36/37 (test_23 - известный, до этой работы).

1.1.1 (FreeCAD-perf): тот же дефект (Part/PD/Sketcher/Mesh/FEM), патч не собран - нет дерева сборки 1.1.1 (как UV7).
