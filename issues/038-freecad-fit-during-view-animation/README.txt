038 - FreeCAD 26.3: «Вписать выделенное» сразу после «Вид справа» работает как «Вписать всё» и уезжает в сторону
(STUMBLES.md 27.09.2026, пункт «не подтверждено»: ViewSelection на двух ссылках в App::Part, view_end_R.png)

ЧТО БЫЛО В СЦЕНАРИИ (scenario_vr6.py s81): v.viewRight(); выделить две ссылки Rail R; ViewSelection; снимок.
На снимке вид не справа (камера на полпути поворота), масштаб как у «Вписать всё», центр не на рельсах.

ИЗОЛЯЦИЯ (C:/dev/occt8-mig/vr6unconf/probe/vselprobe.py, 29 случаев, offscreen, без HD):
- Рамка выделенных ссылок через App::Part, вложенные Part с поворотами, ссылка на Part, масштаб ссылки, элемент
  массива ссылок - ВЕРНА на стоке (c01-c08 PASS). Ошибки в пересчёте положений ссылок нет.
- «Как Fit all» по масштабу: вписывание по описанной сфере (Coin SoOrthographicCamera::viewBoundingBox): два рельса
  по 350 мм дают сферу 0.908 от сферы всей сборки (c01 ratio=0.908). Это штатное правило (вид не зависит от поворота);
  не менялось - решение VF3 ниже.
- Настоящий дефект (класс): вписывание, вызванное, пока идёт анимация вида, сбивается анимацией.
  Сток: c09 (Right анимированно -> Fit selection) FAIL across=13.2 мм, c11 (Iso -> Fit selection) FAIL 42 мм,
  c13 (Right -> Fit all при центре вращения не в центре сцены) FAIL, c14 (макрос v.viewTop(); v.fitAll()) FAIL,
  c15 (перспектива) FAIL, c16 (Front -> Fit selection грани) FAIL. В покое (c10) и когда центр вписывания совпадает
  с центром вращения (c12) - PASS, поэтому дефект «плавающий».

КОРЕНЬ (weekly 019f5c5):
- src/Gui/Navigation/NavigationStyle.cpp:631/664 setCameraOrientation запускает асинхронную FixedTimeAnimation
  (500 мс по умолчанию, UseNavigationAnimations=1 у владельца) вокруг ТЕКУЩЕГО фокуса.
- src/Gui/Navigation/NavigationAnimation.cpp:100/113 FixedTimeAnimation::update каждый кадр ОТНОСИТЕЛЬНО поворачивает
  камеру вокруг запомненного rotationCenter.
- src/Gui/View3DInventorViewer.cpp:4538 viewAll, :4623 viewObjects (Std_ViewFitSelection), :4922 viewBoundBox ставят
  камеру АБСОЛЮТНО от её текущего положения и не трогают идущую анимацию (setCameraOrientation/translateCamera/zoom
  её останавливают, эти - нет). После вписывания анимация продолжает крутить камеру вокруг СТАРОГО центра -> вписанный
  вид уезжает, ориентация доходит до цели уже от чужой точки. animatedViewAll (:4426) крутит вложенный QEventLoop, в
  котором анимация поворота тоже идёт.

ИСПРАВЛЕНИЕ (класс = любое абсолютное вписывание камеры, пока идёт конечная анимация вида):
- NavigationAnimator::finish(): идущую конечную анимацию доводит до конца сразу - setCurrentTime(totalDuration),
  т.е. последний update + onStop(true) (точная целевая ориентация, сигналы finished/completed) - как при обычном конце.
  Бесконечная (вращение после броска, SpinningAnimation) не трогается.
- NavigationStyle::finishAnimating() -> animator->finish().
- View3DInventorViewer::viewAll, viewObjects, viewBoundBox: первым делом navigation->finishAnimating().
  viewAll(factor), viewSelection, ViewSelectionExtend, Python fitAll/viewSelection идут через них.
- Член класса, вскрытый вместе с 039: рамка выделения без размера (одна вершина) - раньше камера высотой 0
  (1.1.1) или вписывание всего тела (26.3, из-за 039). Теперь: вершина в центр при текущем масштабе
  (navigation->translateCamera), ветка только при радиусе описанной сферы == 0.
- Без выделения/без анимации поведение прежнее (c01-c08, c10, c12 = сток).
- Ветка fcD/src mig/vr6-view 16ec8b8 на 2af3f99 (= поставленный 028+033+035); patches-263/0001 применяется и к 019f5c5.

СБОРКА: portable MSVC 14.44, строки компиляции/линковки bld144 (repro/mkmod.py, overlay-исходники, свои заголовки
Navigation*.h первыми в /I; /showIncludes: заголовки fcD/src не подхватывались - 0 строк).
D0: тот же конвейер с исходниками поставки (undovis/src-fix, режим MKMOD_FLAT) = поставленный 1a135f33 кроме
8 байт (метки времени PE) -> объектная база bld144 = поставка. Исправление FreeCADGui.dll 9a0de2e7bbc9ab317539e9ae7068af11.
ABI (repro/abi.txt): экспорты 12230 -> 12232 (+finish, +finishAnimating, -0), импорт +3 (QAbstractAnimation::loopCount,
setCurrentTime, totalDuration - есть в экспорте Qt6Core.dll поставки; отрицательный контроль несуществующего имени = False).

ТЕСТЫ: см. ../039-*/README.txt раздел ТЕСТЫ (общий прогон, один FreeCADGui.dll + PartGui.pyd).

РЕШЕНИЯ (меняемые):
- VF1 доводить анимацию до конца, а не прерывать (stop() оставил бы вид на полпути поворота) и не ждать её (без
  вложенного цикла событий и повторного входа).
- VF2 вращение (Spinning) не трогаем - у бесконечной анимации нет конечного положения.
- VF3 правило вписывания по сфере (Coin) НЕ меняем: оно штатное для Fit all/Fit selection, не зависит от поворота
  вида; «туже» вписывать по проекции - отдельное UX-решение для владельца.
- VF4 вершина: центр при текущем масштабе (так ведут себя CAD-системы; ноль-высота камеры была дефектом 1.1.1).
- VF5 1.1.1 (FreeCAD-perf) не правится: нет дерева сборки FreeCADGui 1.1.1 (как 035).
