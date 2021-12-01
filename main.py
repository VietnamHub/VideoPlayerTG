#!/usr/bin/env python3
# Copyright (C) @subinps
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from utils import (
    play, 
    start_stream,
    startup_check, 
    sync_from_db,
    check_changes
)
from user import group_call, USER
from utils import LOGGER
from config import Config
from pyrogram import idle
from bot import bot
import asyncio
import os

if Config.DATABASE_URI:
    from utils import db


async def main():
    await bot.start()
    Config.BOT_USERNAME = (await bot.get_me()).username
    LOGGER.info(f"{Config.BOT_USERNAME} Started.")
    if Config.DATABASE_URI:
        try:
            if await db.is_saved("RESTART"):
                msg=await db.get_config("RESTART")
                if msg:
                    try:
                        k=await bot.edit_message_text(msg['chat_id'], msg['msg_id'], text="Khởi động lại thành công.")
                        await db.del_config("RESTART")
                    except:
                        pass
            await check_changes()
            await sync_from_db()
        except Exception as e:
            LOGGER.error(f"Đã xảy ra lỗi khi thiết lập cơ sở dữ liệu cho VCPlayerBot, hãy kiểm tra giá trị của DATABASE_URI. Toàn lỗi - {str(e)}", exc_info=True)
            Config.STARTUP_ERROR="Đã xảy ra lỗi khi thiết lập cơ sở dữ liệu cho VCPlayerBot, hãy kiểm tra giá trị của DATABASE_URI. Toàn lỗi - {str(e)}"
            LOGGER.info("Kích hoạt chế độ gỡ lỗi, bạn có thể định cấu hình lại bot của mình bằng lệnh /env.")
            await bot.stop()
            from utils import debug
            await debug.start()
            await idle()
            return

    if Config.DEBUG:
        LOGGER.info("Người dùng đã bật gỡ lỗi, Hiện đang ở chế độ gỡ lỗi.")
        Config.STARTUP_ERROR="Người dùng đã bật gỡ lỗi, Hiện đang ở chế độ gỡ lỗi."
        from utils import debug
        await bot.stop()
        await debug.start()
        await idle()
        return

    try:
        await group_call.start()
        Config.USER_ID = (await USER.get_me()).id
        k=await startup_check()
        if k == False:
            LOGGER.error("Kiểm tra khởi động không được thông qua, bot đang hoạt động")
            await bot.stop()
            LOGGER.info("Kích hoạt chế độ gỡ lỗi, bạn có thể định cấu hình lại bot của mình bằng lệnh /env.")
            from utils import debug
            await debug.start()
            await idle()
            return

        if Config.IS_LOOP:
            if Config.playlist:
                await play()
                LOGGER.info("Đã bật tính năng phát lặp lại và danh sách phát không trống, đang tiếp tục danh sách phát.")
            else:
                LOGGER.info("Đã bật tính năng phát vòng lặp, bắt đầu phát luồng khởi động.")
                await start_stream()
    except Exception as e:
        LOGGER.error(f"Khởi động không thành công, Lỗi - {e}", exc_info=True)
        LOGGER.info("Kích hoạt chế độ gỡ lỗi, bạn có thể định cấu hình lại bot của mình bằng lệnh /env.")
        Config.STARTUP_ERROR=f"Khởi động không thành công, Lỗi - {e}"
        from utils import debug
        await bot.stop()
        await debug.start()
        await idle()
        return

    await idle()
    await bot.stop()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())



