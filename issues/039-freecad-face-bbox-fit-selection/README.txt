039 - FreeCAD 26.3: «Вписать выделенное» для грани (ребра, вершины) вписывает всё тело
(найдено при изоляции пункта STUMBLES.md «ViewSelection на ссылках в App::Part»; класс «рамка выделенных подэлементов
через ссылки/Part/размещения»)

СИМПТОМ: выделить грань (клик в 3D: Asm.L3.RailBox.Face2) -> Std_ViewFitSelection -> камера вписывает всю деталь
350 мм вместо торца 14x15 мм. Так для грани тела верхнего уровня, в Part, через ссылку, через элемент массива ссылок,
для Part::Feature, для ребра и вершины (ребро/вершина: рамка всей детали, потому что грани в неё входят целиком).
Python: obj.ViewObject.getBoundingBox('RailBox.Face2') возвращает рамку всей детали.

КОРЕНЬ: weekly 019f5c5 src/Mod/Part/Gui/SoBrepFaceSet.cpp:791 getBoundingBox = inherited::getBoundingBox.
Механизм рамки подэлемента (src/Gui/ViewProvider.cpp:1218-1227): getDetailPath + SoSelectionElementAction(Append,
secondary=true) помечает деталь (грань) во ВТОРИЧНОМ контексте выделения, затем SoGetBoundingBoxAction по пути; каждый
узел должен считать рамку только помеченных элементов. SoBrepEdgeSet/SoBrepPointSet это делают, SoBrepFaceSet - нет:
апстрим ebf13e20e («PartGui: remove legacy OpenGL from faces/control points», 13.01.2026; фрагмент удалённого кода в
repro/upstream-ebf13e20e-SoBrepFaceSet.patch.txt) вместе с GL-кодом удалил и рамку по вторичному контексту (она не GL,
только читала координаты через SoGLCoordinateElement). В 1.1.1 работало (fc-build/src SoBrepFaceSet.cpp:1029).
Пустой вторичный контекст (выделено ребро/вершина) тоже игнорировался -> грани давали всю рамку.

ИСПРАВЛЕНИЕ: SoBrepFaceSet::getBoundingBox снова читает вторичный контекст:
- нет контекста или «все» -> inherited (сток, байт в байт тот же путь);
- пустой -> грани рамку не дают (как рёбра/точки; так же рисование: GLRender при пустом ctx2 грани не рисует);
- иначе рамка вершин треугольников выбранных граней: обход coordIndex по partIndex с разделителями -1, как
  buildOverlayCoordIndex этого файла (терпит лишние разделители), координаты из SoVertexProperty или
  SoCoordinateElement (как SoVertexShape), индексы вне массива пропускаются.
- Ветка fcD/src mig/vr6-facebbox c67db3f на 946127c (= источник поставленного PartGui G); patches-263/0001
  применяется и к 019f5c5. Кроме Fit selection затрагивает рамку частично показанных ссылок (скрытые грани
  элемента не входят в Fit all) - как у рёбер/точек 26.3 и граней 1.1.1.
- Вершина (рамка без размера) - см. 038: центр при текущем масштабе.

СБОРКА: PartGui.pyd из bld144 (repro/mkmod.py part). D0: контроль (исходник G без правки, тот же конвейер) =
поставленный e5b8412a кроме 8 байт (метки времени PE). Исправление PartGui.pyd d974f0594c10da8cb129b33ee8b4757c.
ABI: экспорты 1490 = поставка, импорт +0/-0.

ТЕСТЫ (общие с 038; C:/dev/occt8-mig/vr6unconf/runs; offscreen; <= 0.3 GB на процесс; каждый <= 3 мин):
- repro/vselprobe.py, 29 случаев класса (c = ссылки/Part/анимация, f = подэлементы): рамка выделения против точной
  рамки (Part.getShape transform=True), для повёрнутой кривой грани - правило Coin SbXfBox3f; критерии: фокус поперёк
  взгляда <= 1e-3 r, высота камеры = 2r(/aspect).
  исправление (rc fix: FreeCADGui 9a0de2e7 + PartGui d974f059): 29/29 PASS (runs/vsel4f, vsel5f).
  ОТРИЦАТЕЛЬНЫЙ КОНТРОЛЬ: сток weekly и поставка 18 FAIL / 11 PASS (runs/vsel4s, vsel4b, vsel5b) - тест ловит оба
  дефекта; только FreeCADGui-исправление (rc gfix): анимационные случаи PASS, граневые FAIL (runs/vsel3g) - дефекты
  независимы.
- FreeCAD: TestPartGui 15, TestPartDesignGui 21 - поставка и исправление OK (runs/t-TestPart*). TestGuiBase (набор
  fcD/gui/TestGuiBase.py, 37 тестов, в т.ч. Workbench.TestNavigationStyle, TestCoinNodeSnapshots, TestViewProviderLink):
  исправление == сток weekly == поставка по всем 37 вердиктам (у стока свои 1 FAIL + 1 ERROR в TestNavigationStyle;
  runs/t-GuiBase-{fix,stock,base2}); первый прогон поставки остановлен сторожем на 27-м тесте (зависание offscreen,
  повтор base2 прошёл) - записано.
- С HD (rc fix + HybridDesign): vselprobe 29/29 PASS (runs/vsel6fhd).
- Пользовательский путь, окно (scenario_vr6 копия, assembly, rc fix): 0 спотыканий, view_end_R.png - вид точно
  справа, правые рельсы в центре кадра (repro/view_end_R.fix.png; до: repro/view_end_R.before.png - поворот на
  полпути и сдвиг). Масштаб по-прежнему по описанной сфере (два рельса 350 мм вдоль взгляда ~ вся сборка, 038 VF3).
- Пункт (a) STUMBLES («task dialog still open after OK» после эскиза): НЕ воспроизведён: repro/okprobe.py 108 закрытий
  offscreen + 53 в окне (5 вариантов: круг/прямоугольник на YZ, эскиз на грани, после LinearPattern, выделение
  плоскости) + 2 полных прогона scenario_vr6 (assembly) - 0 случаев; поставка без HD. Записано, не правилось.

РЕШЕНИЯ (меняемые): FB1 восстановлен смысл 1.1.1, реализация без GL-элемента; FB2 обход с разделителями вместо
жёсткого шага 4 (1.1.1) - на правильных данных то же; FB3 1.1.1 не правится (там работает).
