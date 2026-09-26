# perf/801 — наши правки OCCT поверх V8_0_1 (партия ядра 1)

База: тег `V8_0_1` (b8f597c6), без изменений. Ветка `perf/801`, по коммиту на дефект. Цель — FreeCAD weekly
2026.09.23 (26.3dev, git 019f5c5, OCCT 8.0.1): каждый toolkit собирается целиком и подкладывается в `bin` вместо
стокового файла того же имени.

| Коммит | Дефект | Toolkit | Файлы | Что |
|---|---|---|---|---|
| fac46d86 | 001 | TKFillet | ChFi3d_Builder_C1.cxx | `ChFi3d_Recale` и на замкнутой грани (`onsame \|\| IsUClosed \|\| IsVClosed`): скругление ребра, упирающегося в шов |
| cc6e9785 | 009 | TKBO | BOPTools_AlgoTools2D.cxx | `AdjustPCurveOnSurf`: сдвиг периода учитывается один раз, булевы с гранью шире периода не теряют инструмент |
| 5cef9671 | 012 | TKMesh | BRepMesh_BucketClass2d.hxx (новый), BRepMesh_Classifier, CircleTool, Delaun, FaceChecker, FILES.cmake | классификатор по корзинам (ответы = CSLib_Class2d 8.0.1), растущая сетка описанных окружностей, отсев пар проводов по габаритам |

Полные патчи (каждый применяется к чистому V8_0_1, `git apply --check`):
- `freecad-kernel-fixes/issues/001-occt-fillet-at-seam/patches-801/0002-chfi3d-recale-on-closed-face-V8_0_1.patch`
- `freecad-kernel-fixes/issues/009-occt-bop-periodic-pcurve/patches-801/0001-BOPTools-AdjustPCurveOnSurf-shift-counted-once-V8_0_1.patch`
- `freecad-kernel-fixes/issues/012-occt-brepmesh-quadratic-long-faces/patches-801/0001+0002+0003-BRepMesh-full-V8_0_1.patch`

## Перенос

001 и 009 — те же строки, что в 7.8.1 (перенос `occt8-mig/kernel-src/port`, у 001 один конфликт в скобках).
012 — те же изменения плюс сверка `BRepMesh_BucketClass2d` с CSLib_Class2d **8.0.1** (он переехал в TKMath):
- в тесте ON по ребру пропускаются почти вертикальные отрезки: `std::abs(aEdgeDx) > Precision::PConfusion()`
  (`CSLib_Class2d.cxx:305-306`);
- угловые проверки допуска — только при `myTolU > 0.0 || myTolV > 0.0` (в 7.8.1 — при любом ненулевом, т.е. и
  при отрицательном или NaN);
- массивы точек — члены `NCollection_Array1<double>`, размер задаёт тот же `Resize(0, N, false)`, что и в `init()`
  8.0.1, поэтому выделение и его отказ — стоковые.

## Сборка

`occt8-mig/kb1/tools/build_tk.py <TK> <дерево> <выход> [--toolset <env.bat>]`: все .cxx пакетов toolkit'а, флаги
LibPack 3.5.5 (`/EHa /GR /std:c++17 /O2 /Ob2 /MD /fp:precise`, исключения включены, без LTCG,
`OCC_CONVERT_SIGNALS` не задан), import-библиотеки из экспортов DLL weekly (`mkdef.py`). Через
`C:/dev/tools/buildlock.sh`, `/MP4`.
- Поставляемые DLL: переносной MSVC 14.50 (cl 19.50.35739, `C:/dev/toolchains/msvc-14.50/vcvars150.bat`; OCCT в
  weekly собран 14.50, сборка 35730), с ресурсом версии OCCT (`adm/templates/occt_toolkit.rc.in`, FileVersion
  8.0.1 — как у weekly). Экспорты = weekly (TKMesh 361, TKBO 961, TKFillet 1382; 0 лишних, 0
  недостающих). Импорты контрольных сборок = weekly символ в символ; у 012 +floor/_dclass и −CSLib_Class2d (сам патч).
- Первый набор собран MSVC 14.36 (cl 19.36.32532): те же результаты, но импортирует `_Throw_C_error` и
  `_Mtx/_Cnd_*_in_situ`, поэтому не поставляется.

| DLL (14.50) | md5 |
|---|---|
| 001 TKFillet | 6c6be47d107ffd0f3375547f169eaaa0 |
| 009 TKBO | 7bd2e88d6fbd935f61c608d4ece7b40d |
| 012 TKMesh | abaef4e3b1490f485fec26dba728d9dc |
| контроль TKFillet / TKBO / TKMesh | ef420d49… / 92cf9ddb… / 6c208bf8… |
| weekly (сток) TKFillet / TKBO / TKMesh | 6819298d… / 4ae8f637… / faeb3bbc… |

Файлы: `freecad-kernel-fixes/build/variants801/{001,009,012,control}/` (+ `msvc14.36/`), MD5SUMS.txt в каждой.

## Доказательства (26.09.2026; всё в `C:/dev/occt8-mig/kb1/`, журнал — `occt8-mig/progress.md`)

**D0: контроль = weekly.** Контрольная сборка (чистый V8_0_1, те же флаги и компилятор) в жёсткой копии weekly
даёт на корпусе `occt8-mig/corpus` те же результаты и тот же вывод консоли, что стоковый weekly: скругления,
булевы, сетки, открытие и пересчёт файлов 1.1.1 — 821 значение (объёмы, площади, габариты, isValid, текст
`check(True)`, md5 BREP каждого результата, md5 сеток с порядком треугольников), 0 различий; для 14.36 и для
14.50 (`logs/corpus-compare*.txt`).

**Патч против weekly** (тот же корпус; и каждый патч отдельно, и все три вместе): отличаются только сами дефекты,
консоль совпадает.
- 001: скругление у шва — объём +374,97, `isValid False`, «Bad orientation» → снято 1,368 (идеал 1,367), валидно,
  чисто. DRAW (DRAWEXE из weekly): группа `blend`, 475 журналов — weekly = контроль = патч побайтно (181 OK,
  2 BAD известных, 292 без данных). Отрицательный контроль: «тупой» вариант (Recale безусловно) ломает
  `blend/simple/H4` и `blend/buildevol/D6`, как и на 7.8.1.
- 009: common 0 → 5815,084504 (точно 5815,084489), cut 45600 → 39784,915488, fuse становится валидным. Фазз
  `boolean_fuzz.py` (816 записей): 732 одинаковы, 84 различаются — все 84 неверны на контроле и верны с патчем,
  0 регрессий.
- 012: сетки равны weekly по md5 с порядком: корпус в FreeCAD; meshcmp (strict+canon) — 19 форм общего корпуса
  (3288 граней) и 149 форм корпуса дефекта 012 (5636 граней); `delcmp` (15 наборов). Винт ШВП 6,4° в FreeCAD —
  md5 e757560d…, 1 014 382 треугольника = записанный результат weekly. `classcmp` против CSLib_Class2d из TKMath
  weekly: 13 367 135 запросов, 0 расхождений (сборки харнесса 14.36 и 14.50); копия класса с семантикой 7.8.1 —
  32 456 расхождений. Проверочная сборка (`BREPMESH_FACECHECKER_VERIFY_4B`): 8993 вызова FaceChecker, все равны
  стоковому циклу; мутанты `drop`/`swap` пойманы (4 из 4 граней с отсевом), `FC4B_OOM` wild/tree/list — откат на
  стоковый цикл без отличий, мутант с проброшенным исключением пойман. Мутант допуска (×1000) пойман и meshcmp,
  и прогоном в FreeCAD.
- Скорость (по одному прогону): верхняя грань плиты с 1024 отверстиями 28,5° 3,31 → 0,43 с, пик процесса 495 → 156 МБ;
  винт ШВП 28,5° 1,97 → 1,14–1,45 с, 6,4° 169,4 с (запись weekly) → 15,2–16,9 с. 001 и 009 — в пределах шума.

## Не сделано

- Патчи в `freecad-kernel-fixes/issues/*/patches-801` не закоммичены там: рабочая копия на чужой ветке
  (perf/a-bench), папка 012 целиком не отслеживается.
- Плиты с 1024 отверстиями при 6,4° (shapefix, refine, bad_orient_1024): сток weekly под ограничением 1 ГБ падает
  (rc 139), сравнить нельзя; патч строит их в 247–405 МБ. По правилу 1 ГБ — только на итоговой приёмке.
