# Набор действий владельца (bench)

Замер восьми действий владельца во FreeCAD на копиях его файлов. По этому набору судится каждый патч
ускорения (цель — 10× и больше, спек `docs/superpowers/specs/2026-09-21-mesh-pick-performance-design.md`, §11).
Замер ничего не упрощает в модели: те же файлы, те же настройки владельца (в том числе 6,4° у VR6).

FreeCAD запускается оффскрин (`QT_QPA_PLATFORM=offscreen`), без окна и без ввода мыши/клавиатуры: кадры рисует
`SoOffscreenRenderer` из собственного графа сцены вида, наведение идёт через `SoHandleEventAction` внутри процесса.

## Команды

Один прогон (из `bench/`):

    ./run_bench.sh <tag> <variant> <fc|hd> <FC_DIR> <файл|fixture:имя> <label> <действия,через,запятую>

- `tag` — имя папки `runs/<tag>` (она удаляется и создаётся заново);
- `variant` — имя варианта FreeCAD для отчёта (`stock`, `p012`, ...);
- профиль `fc` — чистый FreeCAD без дополнений; `hd` — плюс HybridDesign из установленного репозитория, только
  чтение, через ключ `-M`;
- `FC_DIR` — корень FreeCAD, например `"C:/Program Files/FreeCAD 1.1"`;
- файл — копия из `bench/files/` или тестовый документ `fixture:pad` (Task 3 добавит `fixture:holes1024`).

Переменные окружения: `BENCH_CUT_BASE` (тело для `edit_cut`), `BENCH_BODY_OBJ` (объект для `edit_body`, по
умолчанию `Pad`), `BENCH_HEAVY` (объект, наведение на который считается отдельно), `BENCH_W`/`BENCH_H` (кадр,
1920×1080), `BENCH_TO` (таймаут, с, по умолчанию 1800).

`run_bench.sh` печатает `exit=<код> tag=<tag> result=yes|NO`. `exit=0` — драйвер дошёл до конца и записал
`result.json` (процесс завершается сразу через `TerminateProcess`: при `os._exit` с HD процесс падал уже после
записи и отдавал 127); `124` — таймаут; `2` — неверные аргументы; `3` — не сделана копия настроек. Ошибки
отдельных действий — в `errors` внутри `result.json`.

Пример — дымовой прогон:

    ./run_bench.sh smoke-fc stock fc "C:/Program Files/FreeCAD 1.1" fixture:pad pad open,orbit,hover,select,edit_body,save

Серия базы — `run_matrix.sh <variant> <FC_DIR> <повторы>` (появится в Task 4). Свод «было → стало»:

    python report.py runs <base_variant> <variant> [reports/<имя>.md]

Тесты сводки (без FreeCAD): `python -m unittest discover -s tests -v`.

## Действия и метрики

| Действие | `result.json` → `actions.<имя>` | Метрика |
|---|---|---|
| Открыть файл в GUI | `open` | `open_s` — `openDocument`; `idle_s` — до простоя цикла событий; `first_frame_ms`, `second_frame_ms`; `gl_init_ms` — создание GL-контекста оффскрин-рендера, отдельно |
| Вращение | `orbit` | медиана и p90 кадра облёта: `overview` (24 кадра) и `closeup` (24 кадра, зум ×6) |
| Наведение и предвыбор | `hover` | отклик предвыбора + кадр подсветки по сетке 16×9: `all`; `heavy` — только точки на `BENCH_HEAVY` |
| Выделение | `select` | `addSelection` → выделено (дерево + 3D) → кадр, до 20 целей |
| Правка параметра в Body | `edit_body` | правка → пересчёт → цикл событий занят → кадр: `edit`; части — `recompute`, `idle`, `frame` |
| Правка STEP-детали (Part::Cut в VR6) | `edit_cut` | то же; плюс `faces` тела и `cut_valid` |
| Скругление на детали с 1024 отверстиями | `fillet_holes` | то же; плюс `valid` |
| Сохранение | `save` | `save_s` и `bytes` |

Сводки (`summary`) — `median`, `p90`, `min`, `max`, `n` в мс. Кроме действий в `result.json` пишутся `env`
(версия FreeCAD, md5 DLL ядра и `Part.pyd`/`PartGui.pyd`, `hd_loaded`, GL-строки — должна быть RTX 3050),
`cpu_load_pct` (загрузка всей машины за прогон: машина общая) и `errors` (трассировки по действиям; упавшее
действие в `actions` не попадает).

## Где лежат результаты

- `runs/<tag>/result.json` — метрики; рядом `fc.log`, `stdout.log`, `cfg.log`, `saved.FCStd`, копии `user.cfg` и
  `system.cfg`, по которым шёл прогон. `runs/` и `files/` в git не попадают.
- `files/` — копии файлов владельца, md5 в `files/MD5SUMS.txt`. Оригиналы не трогаются.

## Правила запуска

- Каждый FreeCAD — только через `C:/dev/tools/fcslot.sh` (так делает `run_bench.sh`), не больше одного FreeCAD
  от одного исполнителя одновременно.
- Настройки владельца копируются заново на каждый прогон (`tools/cfg_sandbox.py`): живой `user.cfg` только
  читается. Если копии нет, `run_bench.sh` не запускает FreeCAD (`exit=3`): на настройках по умолчанию замер
  был бы не про файлы владельца.
- HybridDesign подключается ключом `-M` прямо из установленного репозитория, без ссылок (проверено: `smoke-hd`,
  `hd_loaded: true`). Байткод в него не пишется: `run_bench.sh` кладёт в `userdata/Mod/BenchNoPyc/Init.py`
  `sys.dont_write_bytecode = True` (переменные `PYTHON*` Python во FreeCAD игнорирует).
- **Junction.** Если когда-нибудь HD придётся подключать ссылкой `userdata/Mod/HybridDesign` (junction на
  репозиторий), ссылку надо снимать до `rm -rf "$RUN"` (`cmd //c rmdir <ссылка>`), иначе `rm -rf` сотрёт сам
  репозиторий HD.

## Оговорки оффскрина (измерено)

- Первый GL-контекст процесса создаётся ~1,5 с (загрузка драйвера). Это контекст замера, а не вида FreeCAD,
  поэтому он создаётся до первого кадра и пишется отдельно в `gl_init_ms`; в `first_frame_ms` его нет.
- Оффскрин-рендер ставит графу вида свою область W×H, и в ней же работают `getObjectInfo` и наведение; сетка
  наведения и выделения строится по этой области.
- В правке не считается окно тишины 200 мс, которым `wait_idle` убеждается, что цикл событий закончил: это
  ожидание замера. В `idle` правки маленькой детали входит таймер FreeCAD `activityTimer` (обновление состояния
  команд через ~150 мс после изменения, 7–10 мс работы); иногда — и обработка предупреждений
  `No valid GL context found!` в журнале через ~370 мс (13–16 мс работы), которых в окне не бывает.
- Миниатюра при сохранении оффскрин не рисуется (`imageFromFramebuffer failed`), а у владельца
  `SaveThumbnail=1`: в `save_s` нет рендера миниатюры 256×256.
