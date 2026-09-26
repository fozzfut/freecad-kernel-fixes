# 018 на OCCT 8.0.1 (V8_0_1, b8f597c6)

`0001-BRepCheck-018-V8_0_1.patch` — один патч к чистому `V8_0_1` (`git apply --cached --check` в C:/dev/occt-801: OK;
в рабочей копии с `core.autocrlf=true` FILES.cmake лежит с CRLF — применять `git am`/`git apply` к индексу или с
`core.autocrlf=false`). Коммит `perf/801` 55b0e9ad. Только `src/ModelingAlgorithms/TKTopAlgo/BRepCheck`.

Патчи conda-forge серии 7.8.1 (0001 MakeEdge, 0002 MAT_TList) сюда не входят: 0008 уже upstream (7.9.0, #297),
0010 нет ни в 8.0.1, ни в LibPack weekly — DLL обязана вести себя как weekly.

## Что изменилось против 018 для 7.8.1
- Эталон — сток 8.0.1 с PR #1375 (пропуск пар петель с разнесёнными надёжными боксами в ClassifyWires). Тест #1375
  выполняется для каждой пары с теми же ролями; наши механизмы (точка петли один раз, IsFarOutside, сетка точек)
  — только на парах, которые 8.0.1 ещё классифицирует. На реальных отверстиях #1375 почти не срабатывает:
  у окружности диапазон ребра 2π на ulp больше диапазона кривой, у периодических — сдвиг на π
  (`build-scripts-801/boxprobe.cpp`: плита 1024 — бокс у 1 петли из 1025, Top.FCStd грань 5 — у 1 из 94).
- `BRepCheck_WireClass2d.cxx` сгенерирован из FClass2d 8.0.1 (`build-scripts-801/gen_wireclass2d.py`, md5 исходника
  0f602254…, проверка `--check`). Доказательство IsFarOutside/NearBox переписано под `CSLib_Class2d::SiDans` 8.0.1.
- Развёртки пар по боксам — общий `BRepCheck_BoxPairs.hxx` с запасом 1e-9: быстрый путь `Bnd_Box2d::IsOut` в 8.0.1
  (`Xmin - Other.Xmax > Gap + Other.Gap`) не совпадает побитно с тестом диапазонов `Get()`, на котором стояло
  доказательство 7.8.1; развёртка даёт надмножество, решает тест стока.
- `GetOrientation` (Wire) — `NCollection_Map::Contained()` (константный поиск 8.0.1) вместо `Added()`.
- Сборка проверки `BREPCHECK_VERIFY_018` (env `BRCHK018_BREAK/NOVERIFY/LOG/ALLPAIRS`): сравнение со стоком на каждом
  вызове, счётчики вместо выхода.

## Сборка
`occt8-mig/kb1/tools/build_tk.py TKTopAlgo <дерево> <выход> --toolset C:\dev\toolchains\msvc-14.50\vcvars150.bat`
(флаги LibPack, импорт-библиотеки из экспортов weekly), 0 предупреждений /W4. DLL: `build/variants801/018/`
(md5 2a68043f…), контроль `build/variants801/control/TKTopAlgo.dll` (614aee39…).

## Доказательства (26.09.2026, `C:/dev/occt8-mig/k018/`, журнал — `occt8-mig/progress.md`, раздел lane 018)
Корпус 70 форм (`k018/lists/all.txt`): общий корпус occt8-mig (BREP + фигуры из Top/hicmos/oring FCStd + STEP VR6
part4 и oring через стоковый ридер), bad_wires, синтетика 018 (без 4096) и 6b.
- checkcmp801 (дамп всех статусов по каждому подобъекту и контексту): weekly = контроль 70/70; контроль = 018 70/70;
  параллельный анализатор, 12 форм: 12/12.
- Сборка проверки: 0 расхождений на 70 формах и в режиме «все пары» (classify 36 615, grid ~20 000, fpairs 15 123,
  subshape 105 141, orient 56 532, seams 24 656, surface 40 765, occ 19 858, forient 21 396, nbset 255, pairs 19 вызовов);
  статусы = контроль. Порча `BRCHK018_BREAK=classify/fpairs` ловится (2301 / 7 расхождений).
- classcmp801 (копия против FClass2d weekly): 24 862 петли, 25 962 836 точек, 0 расхождений, 0 FARWRONG, 0 NEAROUT;
  с перевёрнутым OutsideState — rc 1, 2 385 809 FARWRONG.
- Мутанты DLL: m1 (OutsideState перевёрнут) — 43 формы из 70 отличаются от контроля; m2 (ориентация ключа из петли
  грани, а не из карты) — 41 из 70.
- ABI: экспорты 1873 = weekly, 0/0; импорт-символы контроля = weekly.
- Скорость, один парный прогон (машина под нагрузкой, 0,8 ГБ свободно): плита 1024, анализатор грани 1,24 → 0,13 с и
  1,51 → 0,15 с; вся форма (анализатор + IsValid) 3,00 → 0,43 с; скругление плиты + BRepAlgo::IsValid: IsValid
  1,41 → 0,16 с; Top.FCStd грань 94 петли 0,061 → 0,012 с.
