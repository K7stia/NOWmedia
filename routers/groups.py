import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from utils.json_storage import load_groups, save_groups, remove_group, load_known_media
from states.group import AddGroup, RenameGroup
from keyboards.groups import group_menu_kb, channels_group_kb

router = Router()

@router.callback_query(F.data == "menu_groups")
async def cb_manage_groups(callback: CallbackQuery):
    await callback.message.edit_text("Керування групами медіа:", reply_markup=group_menu_kb())

@router.callback_query(F.data == "add_group")
async def cb_add_group(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddGroup.waiting_name)
    await callback.message.edit_text("Введіть назву нової групи:")

@router.message(AddGroup.waiting_name)
async def add_group_name(message: Message, state: FSMContext):
    group_name = message.text.strip()
    if not group_name:
        await message.answer("❗️ Назва не може бути порожньою.")
        return
    groups = load_groups()
    if group_name in groups:
        await message.answer("❗️ Така група вже існує.")
        return
    groups[group_name] = []
    save_groups(groups)
    await state.clear()
    await show_group_edit_menu(message, group_name, mode="selected")

@router.callback_query(F.data.startswith("edit_group|"))
async def cb_edit_group(callback: CallbackQuery):
    group_name = callback.data.split("|", 1)[1]
    await show_group_edit_menu(callback.message, group_name, mode="selected")

@router.callback_query(F.data.startswith("show_all_channels|"))
async def cb_show_all_channels(callback: CallbackQuery):
    group_name = callback.data.split("|", 1)[1]
    await show_group_edit_menu(callback.message, group_name, mode="all")

async def show_group_edit_menu(target, group_name: str, mode: str = "selected"):
    text = (
        f"<b>Група:</b> <u>{group_name}</u>\n"
        "Редагуйте список медіа, що входять у цю групу."
    )
    markup = channels_group_kb(group_name, mode=mode)

    if isinstance(target, Message):
        await target.answer(text, reply_markup=markup, parse_mode="HTML")
    elif isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

@router.callback_query(F.data.startswith("toggle_group_channel|"))
async def toggle_group_channel(callback: CallbackQuery):
    _, media_key, group_name = callback.data.split("|")
    groups = load_groups()
    group = groups.get(group_name, [])
    media = load_known_media()
    media_info = media.get(media_key)

    if not media_info:
        await callback.answer("❗️ Медіа не знайдено.", show_alert=True)
        return

    existing_ids = {c["id"] for c in group if isinstance(c, dict)}
    if media_info["id"] in existing_ids:
        group = [c for c in group if c.get("id") != media_info["id"]]
    else:
        group.append({"id": media_info["id"], "title": media_key})

    groups[group_name] = group
    save_groups(groups)

    new_markup = channels_group_kb(group_name, mode="all")
    await callback.message.edit_reply_markup(reply_markup=new_markup)
    await callback.answer("Оновлено")

@router.callback_query(F.data.startswith("rename_group|"))
async def cb_rename_group(callback: CallbackQuery, state: FSMContext):
    group_name = callback.data.split("|", 1)[1]
    await state.set_state(RenameGroup.waiting_new_name)
    await state.update_data(old_name=group_name)
    await callback.message.edit_text(f"✏️ Введіть нову назву для групи \"{group_name}\":")

@router.message(RenameGroup.waiting_new_name)
async def process_group_rename(message: Message, state: FSMContext):
    new_name = message.text.strip()
    data = await state.get_data()
    old_name = data.get("old_name")

    if not new_name or new_name == old_name:
        await message.answer("⚠️ Назва не змінена.")
        return

    groups = load_groups()
    if new_name in groups:
        await message.answer("❗️ Така група вже існує.")
        return

    channels = groups.pop(old_name, [])
    groups[new_name] = channels
    save_groups(groups)
    await state.clear()
    await message.answer(f"✅ Перейменовано на \"{new_name}\".")
    await show_group_edit_menu(message, new_name, mode="selected")

@router.callback_query(F.data == "list_groups")
async def cb_list_groups(callback: CallbackQuery):
    groups = load_groups()
    if not groups:
        await callback.message.edit_text("ℹ️ Ще не створено жодної групи.")
        return

    buttons = [
        [InlineKeyboardButton(text=f"🔧 {name}", callback_data=f"edit_group|{name}")]
        for name in sorted(groups.keys())
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_groups")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text("📃 Список груп:", reply_markup=kb)

@router.callback_query(F.data == "delete_group")
async def cb_delete_group(callback: CallbackQuery):
    groups = load_groups()
    if not groups:
        await callback.answer("ℹ️ Немає жодної групи для видалення.", show_alert=True)
        return

    buttons = [
        [InlineKeyboardButton(text=f"🗑 {name}", callback_data=f"delete_group_confirm|{name}")]
        for name in sorted(groups.keys())
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_groups")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text("❌ Оберіть групу для видалення:", reply_markup=kb)

@router.callback_query(F.data.startswith("delete_group_confirm|"))
async def cb_delete_group_confirm(callback: CallbackQuery):
    group_name = callback.data.split("|", 1)[1]
    remove_group(group_name)
    await callback.message.edit_text(f"✅ Групу <b>{group_name}</b> видалено.", parse_mode="HTML")
    await cb_manage_groups(callback)
