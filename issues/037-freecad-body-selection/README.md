# 037 — «Создать тело» берёт в базу всё, что выделено (FreeCAD 26.3, PartDesignGui)

Источник: C:/dev/thk-vr6-model/STUMBLES.md, баг 2 (сценарий THK VR6, 27.09.2026). Lane vr6-body.

## Симптом
`Spreadsheet_CreateSheet` → `PartDesign_Body`. Новая таблица остаётся выделенной, и команда пытается сделать её
BaseFeature. Выскакивает модальное окно «Bad base feature: Base feature (Spreadsheet) has an empty shape.».
Тело после OK всё равно создаётся, но без базы.

## Класс
Кандидат в базу тела — только объект, у которого есть собственная Part-геометрия: Part::Feature или GeoFeature,
у которой свойство геометрии — Part-форма. Годится и ссылка, массив ссылок (App::Link с ElementCount > 0) или
цепочка из них, которая в конце ведёт на такой объект. Все остальные объекты не кандидаты:
- таблица, VarSet, текстовый документ, меш, точки;
- App::Part и группа, пустые или с деталями, в том числе активная App::Part; App::LinkGroup;
- плоскость и ось начала координат, App::Origin, App::LocalCoordinateSystem;
- ссылка или массив ссылок на что-то из списка выше (на таблицу, на App::Part, на LinkGroup).

Вопрос «может ли объект стать базой» задают два пути, и оба теперь отвечают одной функцией:
- **«Создать тело» (PartDesign_Body).** Не-кандидатов из выделения команда молча пропускает. Смешанное
  выделение считается только по кандидатам: таблица + деталь дают тело на базе детали, две детали, как и в
  стоке, дают «no more than one feature».
- **Перетаскивание на тело в дереве** (`ViewProviderBody::canDropObject`). Не-кандидата на тело не бросить;
  ветки VarSet, датумов, систем координат, SubShapeBinder и 2D-объектов не менялись.

## Корень
- **Откуда это.** Upstream PR #31763 (8bacbf47c1, 08.08.2026, «PD: Allow BaseFeatures from other App::Parts»).
  Его цель: тело берёт базу из другой App::Part (STEP-импорт с вложенными Part-контейнерами, сборки) и из
  ссылок. Для этого PR убрал запрет «база из чужой Part» и расширил два фильтра:
  - `src/Mod/PartDesign/Gui/CommandBody.cpp:123` (до патча), `CmdPartDesignBody::activated()`:
    `getObjectsOfType(Part::Feature)` стал `getObjectsOfType(App::DocumentObject)`, форму даёт
    `getBaseFeatureShape()` (`Part::Feature::getTopoShape` с ResolveLink);
  - `src/Mod/PartDesign/Gui/ViewProviderBody.cpp:551` (до патча), `canDropObject()`:
    `isDerivedFrom<Part::Feature>` стал `hasBaseFeatureShape()`, то есть «форма не пустая».

  Рецензент PR (kadet1090) просил сделать одну общую функцию вместо повторяющихся проверок; их осталось две.
- **Что сломалось.** Любой выделенный объект стал кандидатом. У таблицы и VarSet форма пустая — модальное окно
  «empty shape». У App::Part, группы и LinkGroup `getTopoShape` даёт компаунд детей: такой объект становится
  базой (активная Part — базой тела, которое лежит в ней же; группа — недействительной BaseFeature). У
  плоскости и оси начала координат — бесконечная база. Смешанное выделение — «no more than one feature», и тела
  нет. Перетаскивание группы, App::Part, LinkGroup или ссылки на Part на пустое тело тоже делает их базой.
- **Upstream.** В main на 27.09 не исправлено (последнее изменение CommandBody.cpp 8a1bdba1dd 22.09 —
  только логирование). Issue про это не нашёл.
- **FreeCAD 1.1.1.** Не затронут: там оба фильтра — `Part::Feature`.

## Исправление (патч patches-263/0001, коммит ec79350 в ветке mig/vr6-body C:/dev/fc-vr6body)
- **Общая функция** `PartDesignGui::canBeBaseFeature()` (Utils.h/Utils.cpp, не экспортируется). Объект
  подходит, если он сам Part::Feature или GeoFeature с `PropertyPartShape`. Иначе функция идёт по ссылкам:
  шаг — `LinkBaseExtension::getTrueLinkedObject(true)`, для прочих объектов — `getLinkedObject(true)`, с
  защитой от циклов.
  - Почему не просто `getLinkedObject(true)`, как в раунде 1: для массива ссылок
    `LinkBaseExtension::extensionGetLinkedObject()` возвращает сам массив, пока ElementCount > 0
    (src/App/Link.cpp:1738), и массив детали терялся.
  - У LinkGroup цели нет, обход на ней кончается.
- **CommandBody.cpp.** Выделение фильтруется через `canBeBaseFeature()` до всех проверок. Всё, что было у
  объектов с формой, осталось как в стоке: чужое тело, PD-фича, молчаливый пропуск Body, путь эскиза,
  датумы PartDesign, предупреждение «empty shape» для Part-фичи без формы, предупреждения о нескольких телах
  или оболочках, ссылки и массивы ссылок на детали, базы из других App::Part.
- **ViewProviderBody.cpp.** Ветка «переместить в тело или сделать базой» в `canDropObject()` требует
  `canBeBaseFeature()` и, как раньше, непустую форму (`hasBaseFeatureShape()` осталась). Всё, что туда
  переносится по `Body::isAllowed` (PD-фичи, Part::Datum, ShapeBinder), — Part::Feature, для них проверка не
  изменилась.
- **Базы.** Ветка построена на поставленной ветке PartDesignGui mig/chamfer cb851d2 (032). Все четыре файла
  совпадают с weekly 019f5c5, поэтому патч ложится и на чистый weekly.

## Сборка
- **Как собрано.** Portable MSVC 14.44, конвейер 032: пересобираются CommandBody.cpp, Utils.cpp,
  ViewProviderBody.cpp (repro/tools/mkone3.py → one3.bat), линк по link.rsp. 0 предупреждений компилятора.
- **D0 control.** Три файла из cb851d2 без изменений (control/PartDesignGui.r2-3files.pyd b2ce4d0a).
  - Объектные файлы против поставленных (repro/tools/coffcmp.py, по секциям): одинаковых секций у
    CommandBody 5680 из 5683, у Utils 4534 из 4538, у ViewProviderBody 4007 из 4010. Различаются только
    .debug$S (пути), .rdata со строкой `__FILE__` (fc-vr6body вместо fc-chamfer) и .chks64.
  - На уровне pyd control отличается от поставленного c3964619 сильнее, на 212393 байта. Причина: имя
    анонимного namespace у MSVC — хеш пути к исходнику (`?A0x28f57398` вместо `?A0x071fa81a`), и порядок
    функций в образе сдвигается.
  - Проверка причины: control-CommandBody + поставленные Utils и ViewProviderBody
    (control/PartDesignGui.hybrid.pyd 53e6227e) отличается от c3964619 на 15 байт.
- **Fix.** 853c19e5. Экспорты 898 = поставленные. Импорты: +2 из FreeCADApp —
  `LinkBaseExtension::getExtensionClassTypeId` и `LinkBaseExtension::getTrueLinkedObject`; оба есть в
  экспортах поставленного FreeCADApp.dll (repro/abi/r2).
- **Где лежат бинарники.** build/variants801/vr6body/{PartDesignGui.pyd, r1/, control/, MD5SUMS.txt}.
  r1/ (a1c9df8b) не ставить.

## Тесты (C:/dev/occt8-mig/vr6body/runs и review/runs, копии в repro/runs и repro/runs/r2)
- **bodysel.py (раунд 2), 49 случаев.**
  - Путь пользователя: выделение в дереве, затем `Gui.runCommand("PartDesign_Body")`, модальные окна
    закрываются автоматически и записываются.
  - Раздел D: перетаскивание на пустое тело через `canDropObject`/`dropObject` провайдера вида (их вызывает
    дерево).
  - 25 членов класса и 24 случая идентичности со стоком: массив ссылок, ссылка на массив, цепочка
    ссылка→ссылка→массив, массив ссылок на ссылку, перетаскивание детали, ссылки, массива, VarSet, эскиза,
    датума, таблицы, меша, пустой Part-фичи.
  - Fix: 49/49 со свежим конфигом (r2-fix2-fresh.txt) и 49/49 с HD (r2-bodysel-fix2-hd.txt).
  - Негативный контроль, поставленный модуль: 24/49. Падают все 25 членов класса, все 24 стоковых случая
    проходят (r2-dlv-fresh.txt).
  - Модуль раунда 1: 39/49. Падают 4 стоковых случая с массивами, «таблица + массив» и 5 членов класса при
    перетаскивании (r2-fixr1-fresh.txt) — это находки ревью R1 и R2.
- **rvprobe.py рецензента, 22 случая, с HD.** Fix 22/22. Перетаскивание: группу и App::Part бросить нельзя,
  массив становится базой Array (r2-rv-fix2-hd.txt).
- **sprobe.py из STUMBLES с HD.** Fix: модального окна нет, тело создано, BaseFeature=None. Поставленный
  модуль: окно «Base feature (Spreadsheet) has an empty shape.» есть (sprobe-dlv-hd.txt).
- **TestPartDesignGui, 21 тест, offscreen.** Поставленный модуль и fix дают одинаковые строки тестов и OK.
  Проверка компаратора: подделанная строка FAIL даёт DIFFERENT.

## Решения (можно поменять)
- **B1.** App::Part, группы и LinkGroup не кандидаты, даже если внутри есть детали. Сток 26.3 делал базой
  компаунд контейнера, а для активной Part получалась циклическая база. Кому нужна база из детали внутри Part,
  выделяет саму деталь — это и был сценарий #31763 (STEP-импорт).
- **B2.** Ссылка или массив ссылок на App::Part тоже не кандидат, как сама Part. Ссылка и массив ссылок на
  Part-объект — кандидат.
- **B3.** Part-фича с пустой формой по-прежнему даёт предупреждение «empty shape»: пользователь выбрал форму,
  и сообщение ему полезно. При перетаскивании пустая форма, как в стоке, просто не принимается.
- **B4.** HD не меняется. `HD_NewBody` (ops/context.new_body) выделение не читает и базу не ставит.
- **B5.** Перетаскивание на тело использует ту же функцию (ревью R2). После B1 «Создать тело» пропускало
  App::Part, а перетаскивание делало её базой. До #31763 эта ветка принимала только Part::Feature.
- **B6.** Свойство BaseFeature в редакторе свойств и в Python (`Body.BaseFeature = ...`) не трогаю: это
  уровень App, а не выбор в интерфейсе.

## Не установлено
Установку делает интеграция: заменить lib/PartDesignGui.pyd в C:/dev/FreeCAD-occt8-perf на 853c19e5.
Предыдущий «наш» файл — c3964619 (032), сток — 615092c6. Если к моменту установки класс-ремедиация R-032
поставит новый PartDesignGui, ветку mig/vr6-body надо перебазировать на неё и пересобрать три файла
(repro/tools/mkone3.py, затем link.bat).

Литература: не применима. Это исправление UX-фильтра, а не алгоритм. Источник — код FreeCAD и PR #31763.
Провенанс: собственный вывод. IP: новых методов нет.
