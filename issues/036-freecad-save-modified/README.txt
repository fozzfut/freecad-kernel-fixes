036 - FreeCAD 26.3: после App.Document.save()/saveAs() из Python документ остаётся «изменённым» (STUMBLES VR6, баг 3, 27.09.2026)

СИМПТОМ (C:/dev/thk-vr6-model/STUMBLES.md, пробы sprobe.py и saveprobe.py): после doc.saveAs(path) и doc.save() у
Gui.getDocument(...).Modified остаётся True. При закрытии FreeCAD спрашивает «Save all changes?», хотя всё уже на диске.
Std_Save флаг снимает. Задевает макросы и скрипты, которые сохраняют через App API (в том числе HD).
Воспроизводится на чистом weekly и на поставке 26.3 perf, с HD и без.

КЛАСС: у документа два хозяина состояния «изменён/сохранён» - App (файл) и Gui (флаг). Любое успешное сохранение
документа В ЕГО СОБСТВЕННЫЙ ФАЙЛ, кто бы его ни начал (Std_Save/Std_SaveAs/Std_SaveAll, Gui.Document.save, App.Document.save/
saveAs, Gui.doCommand из макроса), должно снимать флаг. Сохранение копии в ДРУГОЙ файл (saveCopy), снимок автовосстановления
и неудачное сохранение флаг не снимают.

КОРЕНЬ (weekly 019f5c5, те же строки в mig/undo-vis 2af3f99):
- src/Gui/Document.cpp:1327  Gui::Document::setModified - флаг хранится только в Gui::DocumentP::_isModified; у
                             App::Document такого флага нет.
- src/Gui/Document.cpp:483-540  конструктор подписывается на signalSaveDocument (запись GuiDocument.xml), но НЕ на
                             signalFinishSave - Gui не узнаёт, что App-документ сохранён.
- src/Gui/Document.cpp:1706, 1771, 1848  флаг снимают только сами Gui-пути (save / saveAs / saveAll) после
                             doCommand("App.getDocument().save()"). Путь App.Document.save()/saveAs() (DocumentPyImp.cpp:128/150,
                             App::Document::save Document.cpp:1925 -> saveToFile :1968 -> signalFinishSave :2104) Gui не трогает.
  Почему так: флаг живёт в Gui, потому что его ставят и чисто «видовые» изменения (свойства ViewProvider, которых App не
  видит, ViewProviderDocumentObject.cpp:279). Снятие флага написали в командах Gui, а сигнал конца сохранения
  (signalFinishSave) появился в App позже и использовался только App-наблюдателями (ElementMap, Start, TVStack).
  Upstream: открыт родственный #30581 (File->Save и лишний вопрос при выходе), #19029 (флаг сразу после открытия);
  исправления пути App-сохранения в upstream нет.

ИСПРАВЛЕНИЕ (src/Gui/Document.cpp, +17 строк): Gui::Document подписан на App::Document::signalFinishSave (соединение в
приватном DocumentP, лямбда - без новых экспортов) и снимает флаг, если записанный файл == FileName документа.
- saveToFile испускает signalFinishSave только после записи файла и переименования резервной копии; ошибка записи
  бросает исключение раньше -> флаг остаётся.
- saveCopy пишет файл с другим именем (с именем самого документа отказывается, Document.cpp:1914) -> флаг остаётся.
- снимки автовосстановления (RecoverySnapshot.cpp, Gui AutoSaver) signalFinishSave не испускают -> флаг остаётся.
- Gui-пути как были; их собственное setModified(false) теперь ничего не меняет.
- Тесты FreeCAD: Mod/Test/GuiDocument.py + testAppSaveResetsGuiModified, testSaveCopyAndRecoveryKeepGuiModified.
Ветка fcD/src mig/vr6-save 1a72a61 на mig/undo-vis 2af3f99 (= 028+033+035, поставленный FreeCADGui 1a135f33).
patches-263/0001 применяется и к 019f5c5 (оба файла там те же).

СБОРКА: portable MSVC 14.44, строки компиляции/линковки bld144 (repro/mkgui.py, 5 исходников: 4 из undo-vis + Document.cpp).
D0 контроль (исходники 2af3f99 без правки): bbc68f85 против поставленного 1a135f33 - 37 байт: метки времени PE и строки
__FILE__ трёх исходников (пути той же длины) -> конвейер воспроизводит поставку. Исправление 78052322.
ABI (repro/abi2.py): экспорты 12230 = поставка, импорт 8426 +0/-0 (у контроля тоже). Отрицательный контроль ABI:
FreeCADGui 1.1.1 против поставки: экспорты +484/-1052, импорт +402/-628 - ловится. Предупреждений компилятора 0.

ТЕСТЫ (offscreen, свежие настройки, если не сказано иначе; журналы C:/dev/occt8-mig/vr6save/runs):
- repro/vsprobe.py, 19 случаев (App saveAs/save/getDocument().save, saveCopy, снимок восстановления, видовое изменение,
  отказ записи (файл только для чтения), saveAs без расширения, saveAs в свой файл, два документа, Gui.doCommand,
  Gui.Document.save, Std_Save, закрытие после App save без вопроса):
  поставка 1a135f33 = 10/19 (все 9 FAIL - члены бага, в т.ч. модальное «Save all changes to document 'b'...») = отрицательный
  контроль; исправление 19/19 (fix-fresh) и 19/19 с копией настроек владельца + HybridDesign (fix-owner).
- пробы STUMBLES: saveprobe.py - поставка True/True/True, исправление False/False/False (owner cfg + HD);
  sprobe.py - исправление: after App saveAs/save/Std_Save Modified=False (баг 2 со Spreadsheet остаётся - другая дорожка).
- TestGuiBase (39 с новыми тестами): поставка FAILED failures=2 (новый testAppSaveResetsGuiModified FAIL = отрицательный
  контроль) errors=1; исправление failures=1 errors=1 = собственные FAIL/ERROR стока (NavigationStyle).
  С исходным GuiDocument.py (37 тестов): поставка и исправление - одинаковые вердикты, 35 строк тестов, 157 = 157 сообщений,
  разница только в пути run-копии (rc\dlv против rc\fix) внутри трейсбека стокового ERROR.
  Шум offscreen «This plugin does not support raise() / resource deadlock would occur» (V3 из дорожки exithang) бывает на
  обоих бинарниках в разном количестве (поставка 0 и 1, исправление 1 и 4 на двух одинаковых прогонах) - шум платформы.
  Один прогон исправления (t-TestGuiBase-fix-orig) остановлен сторожем на TestCoinNodeSnapshots (нет роста журнала 120 с,
  машина загружена 98-100 % CPU другими процессами); повтор прошёл до конца. Код сохранения там не вызывается.
- TestPartDesignGui 21: поставка = исправление, SUITE-COMPARE SAME.
RAM <= 406 МБ на процесс.

НЕ ПОКРЫТО: FreeCAD 1.1.1 / «FreeCAD perf» (C:/dev/FreeCAD-perf) - нет дерева сборки FreeCADGui 1.1.1.
Не установлено (установку делает интеграция). Кандидат: build/variants801/vr6save/FreeCADGui.dll 780523228bbcd67e3a5455c0c8dd095a.
