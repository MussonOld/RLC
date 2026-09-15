# -*- coding: utf-8 -*-
"""
Генератор FUNCTIONS.md и rename_functions.py из единого источника — gen.py.
Запуск: python3 build.py
Ничего не пишется вручную в оба выходных файла — только сюда, в FUNCS.
"""
exec(open(__file__.rsplit('/',1)[0]+'/functions_data.py').read())

CONF_ORDER = {"CONFIRMED": 0, "PROBABLE": 1, "SKIP": 2}
CONF_LABEL = {
    "CONFIRMED": "CONFIRMED",
    "PROBABLE": "PROBABLE",
    "SKIP": "не переименовывать (см. примечание)",
}

rows = sorted(FUNCS, key=lambda r: (CONF_ORDER[r[3]], r[0]))

# ---------- FUNCTIONS.md ----------
md = []
md.append("# Справочник функций — nRLC_2_0_12_FREEWARE\n")
md.append(
    "Автоматически собран из `REVERSE_STATUS.md` (не редактировать вручную — "
    "правки вносить в `gen.py` в этом же коммите и пересобирать через "
    "`build.py`). Источник истины по-прежнему `REVERSE_STATUS.md`; это "
    "производная таблица для быстрого поиска по адресу/имени.\n"
)
md.append(
    "Колонка **Уверенность**: `CONFIRMED` — подтверждено прямым чтением "
    "кода/`.hex`; `PROBABLE` — сильная гипотеза, не доказано до конца; "
    "остальные (адрес не существует в дампе, не подтверждён для версии "
    "2.0.12, либо роль вообще не установлена) вынесены в отдельный список "
    "внизу и не участвуют в `rename_functions.py`.\n"
)

md.append("## CONFIRMED\n")
md.append("| Адрес | Предлагаемое имя | Роль | Раздел |")
md.append("|---|---|---|---|")
for addr, name, role, conf, sect in rows:
    if conf == "CONFIRMED":
        md.append(f"| `0x{addr.upper()}` | `{name}` | {role} | {sect} |")

md.append("\n## PROBABLE\n")
md.append("| Адрес | Предлагаемое имя | Роль | Раздел |")
md.append("|---|---|---|---|")
for addr, name, role, conf, sect in rows:
    if conf == "PROBABLE":
        md.append(f"| `0x{addr.upper()}` | `{name}` | {role} | {sect} |")

md.append(
    "\n## Не переименовывать (адрес не существует / не подтверждён для "
    "2.0.12 / роль не установлена)\n"
)
md.append("| Адрес | Рабочее имя | Примечание | Раздел |")
md.append("|---|---|---|---|")
for addr, name, role, conf, sect in rows:
    if conf == "SKIP":
        md.append(f"| `0x{addr.upper()}` | `{name}` | {role} | {sect} |")

md.append(f"\n---\nВсего записей: {len(rows)}.\n")

open(__file__.rsplit('/',2)[0]+'/FUNCTIONS.md', 'w', encoding='utf-8').write('\n'.join(md) + '\n')

# ---------- rename_functions.py (Ghidra script) ----------
py = []
py.append("# -*- coding: utf-8 -*-")
py.append("# Ghidra-скрипт: переименовывает функции и ставит комментарии.")
py.append("# Сгенерировано из REVERSE_STATUS.md (см. FUNCTIONS.md в том же коммите).")
py.append("# Только CONFIRMED и PROBABLE записи — SKIP-адреса сюда не попадают")
py.append("# намеренно (либо не существуют в этом дампе, либо не подтверждены")
py.append("# для версии 2.0.12 — переименовывать их значило бы внести в Ghidra")
py.append("# непроверенную информацию).")
py.append("# Запуск: Ghidra -> Script Manager -> добавить эту папку -> запустить.")
py.append("")
py.append("from ghidra.program.model.symbol import SourceType")
py.append("")
py.append("currentProgram_ = currentProgram")
py.append("fm = currentProgram_.getFunctionManager()")
py.append("")
py.append("# (addr_hex, new_name, comment, confidence)")
py.append("ENTRIES = [")
for addr, name, role, conf, sect in rows:
    if conf in ("CONFIRMED", "PROBABLE"):
        comment = f"[{conf}, раздел {sect}] {role}"
        comment = comment.replace('"""', "'''")
        py.append(f'    ("{addr}", "{name}", """{comment}""", "{conf}"),')
py.append("]")
py.append("")
py.append("renamed, skipped_missing, failed = 0, 0, 0")
py.append("for addr_hex, new_name, comment, conf in ENTRIES:")
py.append("    addr = currentProgram_.getAddressFactory().getAddress(\"0x\" + addr_hex)")
py.append("    func = fm.getFunctionAt(addr)")
py.append("    if func is None:")
py.append("        print(\"SKIP (no function at address): 0x%s\" % addr_hex)")
py.append("        skipped_missing += 1")
py.append("        continue")
py.append("    try:")
py.append("        func.setName(new_name, SourceType.USER_DEFINED)")
py.append("        func.setComment(comment)")
py.append("        renamed += 1")
py.append("    except Exception as e:")
py.append("        print(\"FAILED 0x%s -> %s: %s\" % (addr_hex, new_name, e))")
py.append("        failed += 1")
py.append("")
py.append("print(\"Renamed: %d, missing-at-address: %d, failed: %d\" % (renamed, skipped_missing, failed))")

open(__file__.rsplit('/',2)[0]+'/rename_functions.py', 'w', encoding='utf-8').write('\n'.join(py) + '\n')

print("wrote FUNCTIONS.md and rename_functions.py")
print("CONFIRMED:", sum(1 for r in rows if r[3]=="CONFIRMED"))
print("PROBABLE:", sum(1 for r in rows if r[3]=="PROBABLE"))
print("SKIP:", sum(1 for r in rows if r[3]=="SKIP"))
