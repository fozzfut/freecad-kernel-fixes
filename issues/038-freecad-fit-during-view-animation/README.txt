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

======================================================================================================================
РАУНД 2 (27.09.2026, ответ на ревью r1: R1 MAJOR - класс не закрыт; R2 - пересборка на поставленном 035-PE)

R1. КЛАСС ШИРЕ ВПИСЫВАНИЯ: любая АБСОЛЮТНАЯ установка камеры, пока идёт конечная анимация вида.
Корень тот же: src/Gui/Navigation/NavigationAnimation.cpp:100/113 FixedTimeAnimation::update поворачивает/сдвигает
камеру ОТНОСИТЕЛЬНО прошлого кадра вокруг запомненного центра; HomeAnimation (поставка, View3DInventorViewer.cpp:4559)
каждый кадр пишет свою позу поверх. Кто поставил камеру абсолютно, того анимация уводит (или затирает).
Сток сам следует правилу «новая установка останавливает идущую анимацию» в NavigationStyle::setCameraOrientation
(:648 animator->stop()) и translateCamera (:693), zoom (:989); без него остались:
- View3DInventorViewer::applyCameraState (:4247) = Python setCamera, Std_FreezeViews (CommandView.cpp:516),
  восстановление камеры TempoVis после эскиза (Mod/Show/SceneDetails/Camera.py:50), BIM ArchSectionPlane.py:912;
- View3DInventorViewer::setViewDirection (:3655) = Python setViewDirection;
- View3DInventorPy::viewDefaultOrientation (View3DPy.cpp:697);
- moveCameraTo (:4307) = Python viewPosition: с анимацией уже останавливал через startAnimation; теперь явно всегда.
ИСПРАВЛЕНИЕ (af4d3f4, patches-263/0002): эти места сначала navigation->stopAnimating() (как setCameraOrientation),
потом ставят камеру. Вписывания (viewAll/viewObjects/viewBoundBox) по-прежнему ДОВОДЯТ анимацию до конца (раунд 1, VF1:
ориентация, которую нажал пользователь, сохраняется); абсолютная поза целиком заменяет цель старой анимации - поэтому stop.
Вращение (Spinning) при setCamera тоже останавливается - как у стокового setCameraOrientation (решение VF6).

ОТВЕРГНУТО (проверено измерением): «анимация сама уступает, если позу камеры поменял кто-то другой». По полю камеры
абсолютную запись не отличить от относительной: зум, панорама, поворот влево/вправо, орбита HD (orbit.py) - тоже записи
поля во время анимации, а сток с ними обращается по-своему (b01: поворот влево во время Right - конечный щелчок onStop
ставит точную цель Right, поворот теряется; b02: zoomIn останавливает поворот на полпути). Общий детектор поменял бы
эти случаи. Граница класса: прямые записи полей камеры из Python/модулей (напр. Sketcher centerSelection) остаются как
в стоке; для них есть view.stopAnimating().

ТЕСТЫ (раунд 2, offscreen, <= 0.41 ГБ, каждый прогон 16-27 с; run copies vr6unconf/rc/{dlv2 = поставка 7af65a21,
fix2 = поставка + FreeCADGui 39a66e0c + PartGui d974f059}; runs/r2c-*, r2-*, t2-*):
- repro/r2probe.py: a01 setCamera во время Right, a02 во время Home (HomeAnimation), a03 setCamera С ТОЙ ЖЕ ориентацией
  во время анимации сдвига, a04 viewPosition, a05 viewDefaultOrientation, a06 setViewDirection: fix 6/6 PASS
  (угол <= 9e-6 град, across 0); поставка 1/6 (a04 уже был защищён) - a01 56.6 град/110.7 мм, a02 15 град/136 мм,
  a03 67.8 мм, a05 90 град, a06 125 град. Тождество b01/b02 (CAM равны точно), b03 (4e-5 мм, шум таймера);
  отрицательные контроли n01 setCamera в покое, n02 setViewDirection в покое - PASS на обоих. i01 (INFO) setCamera во
  время вращения: fix 0 град (вращение остановлено), поставка 35 град.
- Пробы ревьюера без изменений: rvprobe r01 fix PASS (поставка FAIL across 110 ddir 0.919), r01n PASS оба; остальные
  случаи rvprobe = как в ревью (r21 FAIL - ожидание пробы без сдвига ссылки, отмечено ревьюером). skcam (эскиз открыть и
  сразу закрыть): fix k1 9/9 PASS без HD и 3/3 с HD + копия конфигурации поставки; поставка k1 3/6 FAIL без HD
  (зависит от момента закрытия), 3/3 FAIL с HD (49-52 мм, 55 град); k0 PASS везде.
- vselprobe 29/29 на fix2. TestGuiBase 37: вердикты fix == поставка (сток: 1 FAIL + 1 ERROR, 7 skipped); первый
  прогон поставки остановлен сторожем на тесте 27 (offscreen, как в раунде 1), повтор полный; отрицательный контроль
  компаратора (подменённая строка) - пойман.
- Ошибка первой версии пробы (исправлена, записано): угол через acos от float32-скаляра давал 0.015 град для ОДИНАКОВЫХ
  кватернионов (|q|^2 = 1 - 3.6e-8); теперь atan2 от нормированных значений.

R2. СБОРКА на mig/undo-vis-pe 3eccec5 (= поставленный 7af65a21): ветка fcD/src mig/vr6-view2 = 89d3ff9 (r1 16ec8b8,
перенесён без изменений - тело патча 0001 то же) + af4d3f4. Компилируются 8 исходников (View3DInventorViewer,
NavigationStyle, NavigationAnimator, View3DPy, View3DViewerPy, CommandView, Tree, propertyeditor/PropertyItem),
0 предупреждений. D0: пять исходников 035-PE через этот конвейер из пути той же длины = 7af65a21 кроме 47 байт (метки
времени PE, __FILE__ одинаковой длины x3, хэш RTTI анонимного пространства). FIX FreeCADGui.dll
39a66e0ca579c0607d5242c716f4e45f; ABI (repro/abi-r2.txt): к поставке exports +2 (r1) imports +3 QtCore (r1); r1->r2 +0/-0.
git merge-tree mig/vr6-view2 с mig/vr6-save 1a72a61 и mig/vr6-asm 01c0dbd - без конфликтов. Оба патча применяются и к
weekly 019f5c5, и к 3eccec5 (git apply --check). PartGui 039 (d974f059) не менялся, база e5b8412a не менялась.
НЕ УСТАНОВЛЕНО (интеграция): bin/FreeCADGui.dll 7af65a21 -> 39a66e0c (earlier ours 7af65a21 1a135f33 d5b15879 680c370e),
lib/PartGui.pyd e5b8412a -> d974f059. Бинарники: build/variants801/vr6view2.

Мелкие замечания ревью: m1 (вершина только в viewObjects; viewAll одной точки даёт h 0.5455 - видимого дефекта нет) -
оставлено; m2 (вращение при вписывании) - решение VF2 оставлено; m3 - согласен. (a) - не воспроизведено, закрыто.
РЕШЕНИЯ (меняемые): VF6 абсолютная поза = stop (как стоковый setCameraOrientation), вписывание = finish (VF1);
VF7 без общего детектора внешних записей (см. ОТВЕРГНУТО).

РАУНД 3 (27.09.2026, ответ на ревью r2: R1 MAJOR - resetToHomePosition; m1 Sketcher; m2 обратная пара с seek; m3 порядок)

КЛАСС (уточнён): движение камеры, которое само ставит позу каждый кадр (FixedTimeAnimation/HomeAnimation - относительные
шаги, Coin seek - абсолютная интерполяция 0.4 с), не должно продолжаться, когда камеру поставил кто-то другой или
началось другое движение: побеждает последнее.

R1. КОРЕНЬ: src/Gui/Quarter/SoQTQuarterAdaptor.cpp:571 resetToHomePosition копирует сохранённую камеру абсолютно
(copyFieldValues / convert*2*) и не останавливает идущую анимацию. Путь пользователя: Std_RecallWorkingView (клавиша End,
View3DInventor.cpp:456 "RecallWorkingView") и Std_ViewRestoreCamera (CommandView.cpp:368). Контроль ревьюера d01s
(view.stopAnimating() перед командой) = PASS - доказывает причину.
ИСПРАВЛЕНИЕ (10f9f7b, patches-263/0003): View3DInventorViewer переопределяет resetToHomePosition (виртуальная в
SoQTQuarterAdaptor, как уже переопределён setSeekMode): если есть камера и сохранённая поза - stopAnimating(), затем
унаследованный. Все вызовы виртуальные (dumpbin: ни один объект не зовёт SoQTQuarterAdaptor::resetToHomePosition
напрямую; vtable View3DInventorViewer только в View3DInventorViewer.cpp.obj). Граница: подклассы в других модулях
(CAM Dummy3DViewer, MatGui AppearancePreview) собраны со старым заголовком - у них стоковый restore (анимаций нет).

m2. SEEK - тоже движение камеры. Новое SoQTQuarterAdaptor::endSeek(finish): остановить идущий seek (где он есть,
или в его конечной позе); seek из режима seek заканчивается как сам (setSeekMode(false)), seek прямо из кода
(Python seekToPoint) режимы не трогает.
- NavigationStyle::startAnimating: новая анимация сначала завершает seek (stop) - как NavigationAnimator::start
  останавливает идущую анимацию. Раньше конец seek (setSeekMode(false) -> stopAnimating) убивал поворот (d08).
- View3DInventorViewer::seekToPoint (две перегрузки скрывают Quarter): перед seek останавливают анимацию вида (как
  setSeekMode(true) перед выбором точки). Все вызовы Quarter seekToPoint - в собранных файлах (NavigationStyle,
  View3DInventorViewer, View3DViewerPy, сам адаптер).
- Вписывания (viewAll/viewObjects/viewBoundBox) доводят seek до конца (finish), как и анимацию (VF1);
  setCameraOrientation/translateCamera рядом со стоковым animator->stop() завершают seek;
  View3DInventorViewer::stopAnimating (Python view.stopAnimating, DemoMode) останавливает и анимацию, и seek
  (объявленное изменение); setSeekMode оставлен стоковым (только анимация навигации).
- Граница: интерактивные стоковые остановки (перетаскивание, панорама, колесо) seek не трогают - при seek из режима
  события мыши и так идут мимо стиля навигации.

m3. Порядок «проверка, стоп, установка» одинаков: setViewDirection и viewDefaultOrientation сначала проверяют блокировку
ориентации (canChangeCameraOrientation), и только потом останавливают. l01 (setViewDirection при блокировке во время
Right): поставка PASS, r2 FAIL 90 град (поворот остановлен зря), r3 PASS.

m1. Sketcher ViewProviderSketch::centerSelection пишет camera->position абсолютно: исправлено в ИСХОДНИКЕ
(mig/vr6-sketch-m1 1ddce71, patches-263/0004: viewer->stopAnimating() перед записью; экспорт уже есть в поставленной
FreeCADGui, совместимо), НО SketcherGui.pyd в этой полосе НЕ собирается: в поставке стоковый бинарник weekly, в
bld144 SketcherGui не собран вовсе; замена целого модуля ради пути «двойной щелчок по ограничению в первые 0.5 с
поворота к эскизу» - несоразмерный риск тождественности. Решение VF8 (меняемое): собрать при первой полосе, которая
всё равно пересобирает SketcherGui.

СБОРКА: MSVC 14.44, tools/mkmod.py target gui3 = 9 исходников (8 раунда 2 + Quarter/SoQTQuarterAdaptor.cpp), 0
предупреждений. Изменённый заголовок View3DInventorViewer.h включается ОТНОСИТЕЛЬНО из Selection/SoFCUnifiedSelection.h,
а файлы moc включают заголовки по пути fcD - поэтому overlay несёт ВСЁ дерево заголовков src/Gui того же коммита
(repro/mirror_gui_headers.py), копии 4 moc с перенаправленным include, и каталоги -I подпапок Gui берутся из overlay
первыми (showIncludes: ни один заголовок не включён по двум путям). D0: control (3eccec5 тем же конвейером) против
control раунда 2 = 34 байта (метки PE, цифра пути overlay, 2 хэша RTTI анонимных пространств); имена экспорта control
== поставка 12230/12230. FIX FreeCADGui.dll 4e89623d165f83db00a4abfd32f1692f: к поставке +6 имён экспорта (r1: finish,
finishAnimating; r3: endSeek, View3DInventorViewer::resetToHomePosition, seekToPoint x2), -0; импорт +3 QtCore (r1);
r2 -> r3 импорт +0/-0 (repro/abi-r3.txt, полная таблица имён - pefile обрезает на 8192). Патчи 0001-0004
применяются к weekly 019f5c5 и к 3eccec5; git merge-tree с mig/vr6-save, vr6-asm, r028, r030, vr6-body - без конфликтов.

ТЕСТЫ (offscreen, <= 0.28 ГБ; run copies vr6unconf/rc/{dlv3 = поставка 7af65a21 + e5b8412a, fix3 = + 4e89623d +
d974f059}; runs3/*):
- ревью d01/d02 (End / Restore camera во время Right): fix3 PASS в 3 прогонах из 3; поставка FAIL 56.6 град /
  110.7 мм в 2 из 3 (в первом прогоне под 100 % CPU поворот успел закончиться до команды - d01 PASS, d02 FAIL);
  n11 (в покое, отрицательный контроль) PASS везде; d01s PASS везде; d03-d06 fix3 PASS (поставка 4 FAIL).
- seek (repro/r3probe.py): s01 Right во время seek: fix3 PASS, поставка FAIL 56.6 град (= d08); s04 setCamera и s05
  End во время seek: fix3 PASS, поставка FAIL 176.5 мм; s07 view.stopAnimating во время seek: fix3 стоит, поставка
  двигается; s02 seek во время Right и s03 вписывание во время seek: PASS оба; s06 seek в покое (контроль) PASS оба.
  d07 (Python seek во время Right): fix3 ровно на точке (q 0.707107,0,0,0.707107), поставка смесь.
- l01/l02 (m3): PASS fix3 и поставка; r2 fix2 l01 FAIL 90 град (отрицательный контроль изменения m3).
- e01 (перспектива во время Right): CAM fix3 = поставка с точностью 2e-3 мм (шум таймера, как в раунде 2).
- прежние: vselprobe 29/29; rvprobe fix3 = раунд 2 (r21 - ожидание пробы, отмечено ревью), поставка 11 FAIL;
  skcam k1 3/3 PASS (поставка 3/3 FAIL), k0 PASS оба; (a) okexact 34 закрытия, 0 спотыканий (всего 267).
- TestGuiBase 37: вердикты fix3 == поставка (1 FAIL + 1 ERROR + 7 skipped - сток); контроль компаратора пойман.
НЕ УСТАНОВЛЕНО (интеграция): bin/FreeCADGui.dll 7af65a21 -> 4e89623d, lib/PartGui.pyd e5b8412a -> d974f059
(build/variants801/vr6view3, + control/, MD5SUMS). r1 9a0de2e7 и r2 39a66e0c - не ставить.
