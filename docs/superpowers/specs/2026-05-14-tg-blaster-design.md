# TG Blaster — Design Spec

**Date:** 2026-05-14  
**Status:** Approved

## Overview

Desktop application for sending bulk messages (text + photo) to Telegram service chats from a personal Telegram account. Built with Python, Telethon, and CustomTkinter.

## Goals

- Connect a personal Telegram account via Telethon (MTProto)
- Manage a manually curated list of target chats
- Manage saved message templates (text + photo per template)
- Send a selected template to all chats with a 5-second delay between each send
- Show a send log in real time

## Non-Goals

- Scheduling / delayed sends
- Analytics or statistics
- Auto-discovery of chats
- Bot API (personal account only)

## Architecture

**Location:** `D:\tg-blaster\`

```
D:\tg-blaster\
├── main.py              # entry point, GUI root
├── telegram_client.py   # Telethon auth + send logic
├── storage.py           # JSON read/write helpers
├── requirements.txt
├── data\
│   ├── chats.json       # list of chat usernames/links
│   ├── templates.json   # templates: name, text, photo path
│   └── photos\          # copies of template photos
└── session.session      # Telethon session (auto-created)
```

**Dependencies:**
- `telethon` — Telegram MTProto client
- `customtkinter` — modern desktop GUI
- `pillow` — image preview in GUI

## Data Formats

**chats.json**
```json
["@chat1", "@chat2", "https://t.me/chat3"]
```

**templates.json**
```json
[
  {
    "id": "uuid",
    "name": "Название шаблона",
    "text": "Текст объявления...",
    "photo": "data/photos/uuid.jpg"
  }
]
```

## Telegram API Credentials

Telethon requires `API_ID` and `API_HASH` from https://my.telegram.org.  
These are stored in a `config.json` file in the project root (not committed to git).

```json
{
  "api_id": 123456,
  "api_hash": "abc123..."
}
```

First-time setup: if `config.json` is missing, the app shows a one-time setup screen asking for these values before the auth screen.

## Screens

### Auth Screen (first launch only)
Shown when no `session.session` exists.

1. Phone number input field
2. "Get Code" button → Telegram sends SMS/app notification
3. Code input field
4. "Login" button → session saved, main window opens

After session is saved, auth screen never appears again.

### Main Window — 3 Tabs

#### Tab 1: Templates
- List of saved templates (name + photo thumbnail)
- Buttons: Add, Edit, Delete
- Add/Edit opens a dialog: template name, text area, photo picker (file dialog)
- Photo is copied into `data/photos/` on save

#### Tab 2: Chats
- List of chat usernames/links
- Buttons: Add, Delete
- Add opens a simple input dialog (accepts @username or t.me/link)

#### Tab 3: Broadcast
- Dropdown to select a template
- Preview: shows template text and photo thumbnail
- "Change Photo" button (overrides template photo for this send only)
- "Send to All Chats" button
- Progress log area below (scrollable text): shows each chat sent + errors

## Broadcast Flow

1. User selects template on Broadcast tab
2. Optionally changes photo (temporary override, does not save to template)
3. Clicks "Send to All Chats"
4. App iterates through `chats.json`:
   - Sends photo + caption to chat
   - Waits 5 seconds
   - Logs result (success / error) to log area
5. Shows "Done" when all chats processed

## Error Handling

- Chat not found / access denied → log the error, continue to next chat
- Telegram FloodWait → respect the wait time Telegram returns, log it
- Auth failure → show error dialog, prompt re-login

## File: requirements.txt

```
telethon
customtkinter
pillow
```
