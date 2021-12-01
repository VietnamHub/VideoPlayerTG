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

from .logger import LOGGER
try:
    from pyrogram.raw.types import InputChannel
    from apscheduler.schedulers.asyncio import AsyncIOScheduler   
    from apscheduler.jobstores.mongodb import MongoDBJobStore
    from apscheduler.jobstores.base import ConflictingIdError
    from pyrogram.raw.functions.channels import GetFullChannel
    from pytgcalls import StreamType
    import yt_dlp
    from pyrogram import filters
    from pymongo import MongoClient
    from datetime import datetime
    from threading import Thread
    from math import gcd
    from .pyro_dl import Downloader
    from config import Config
    from asyncio import sleep  
    from bot import bot
    from PTN import parse
    import subprocess
    import asyncio
    import json
    import random
    import time
    import sys
    import os
    import math
    from pyrogram.errors.exceptions.bad_request_400 import (
        BadRequest, 
        ScheduleDateInvalid,
        PeerIdInvalid,
        ChannelInvalid
    )
    from pytgcalls.types.input_stream import (
        AudioVideoPiped, 
        AudioPiped,
        AudioImagePiped
    )
    from pytgcalls.types.input_stream import (
        AudioParameters,
        VideoParameters
    )
    from pyrogram.types import (
        InlineKeyboardButton, 
        InlineKeyboardMarkup, 
        Message
    )
    from pyrogram.raw.functions.phone import (
        EditGroupCallTitle, 
        CreateGroupCall,
        ToggleGroupCallRecord,
        StartScheduledGroupCall 
    )
    from pytgcalls.exceptions import (
        GroupCallNotFound, 
        NoActiveGroupCall,
        InvalidVideoProportion
    )
    from PIL import (
        Image, 
        ImageFont, 
        ImageDraw 
    )

    from user import (
        group_call, 
        USER
    )
except ModuleNotFoundError:
    import os
    import sys
    import subprocess
    file=os.path.abspath("requirements.txt")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', file, '--upgrade'])
    os.execl(sys.executable, sys.executable, *sys.argv)

if Config.DATABASE_URI:
    from .database import db
    monclient = MongoClient(Config.DATABASE_URI)
    jobstores = {
        'default': MongoDBJobStore(client=monclient, database=Config.DATABASE_NAME, collection='scheduler')
        }
    scheduler = AsyncIOScheduler(jobstores=jobstores)
else:
    scheduler = AsyncIOScheduler()
scheduler.start()
dl=Downloader()

async def play():
    song=Config.playlist[0]    
    if song[3] == "telegram":
        file=Config.GET_FILE.get(song[5])
        if not file:
            file = await dl.pyro_dl(song[2])
            if not file:
                LOGGER.info("Tải xuống tệp từ telegram")
                file = await bot.download_media(song[2])
            Config.GET_FILE[song[5]] = file
            await sleep(3)
        while not os.path.exists(file):
            file=Config.GET_FILE.get(song[5])
            await sleep(1)
        total=int(((song[5].split("_"))[1])) * 0.005
        while not (os.stat(file).st_size) >= total:
            LOGGER.info("Đang chờ tải xuống")
            LOGGER.info(str((os.stat(file).st_size)))
            await sleep(1)
    elif song[3] == "url":
        file=song[2]
    else:
        file=await get_link(song[2])
    if not file:
        if Config.playlist or Config.STREAM_LINK:
            return await skip()     
        else:
            LOGGER.error("Luồng này không được hỗ trợ, rời khỏi VC.")
            await leave_call()
            return False 
    link, seek, pic, width, height = await chek_the_media(file, title=f"{song[1]}")
    if not link:
        LOGGER.warning("Liên kết không được hỗ trợ, Đang bỏ qua khỏi hàng đợi.")
        return
    await sleep(1)
    if Config.STREAM_LINK:
        Config.STREAM_LINK=False
    LOGGER.info(f"BẮT ĐẦU CHƠI: {song[1]}")
    await join_call(link, seek, pic, width, height)

async def schedule_a_play(job_id, date):
    try:
        scheduler.add_job(run_schedule, "date", [job_id], id=job_id, run_date=date, max_instances=50, misfire_grace_time=None)
    except ConflictingIdError:
        LOGGER.warning("Điều này đã được lên lịch")
        return
    if not Config.CALL_STATUS or not Config.IS_ACTIVE:
        if Config.SCHEDULE_LIST[0]['job_id'] == job_id \
            and (date - datetime.now()).total_seconds() < 86400:
            song=Config.SCHEDULED_STREAM.get(job_id)
            if Config.IS_RECORDING:
                scheduler.add_job(start_record_stream, "date", id=str(Config.CHAT), run_date=date, max_instances=50, misfire_grace_time=None)
            try:
                await USER.send(CreateGroupCall(
                    peer=(await USER.resolve_peer(Config.CHAT)),
                    random_id=random.randint(10000, 999999999),
                    schedule_date=int(date.timestamp()),
                    title=song['1']
                    )
                )
                Config.HAS_SCHEDULE=True
            except ScheduleDateInvalid:
                LOGGER.error("Không thể lên lịch VideoChat, vì ngày không hợp lệ")
            except Exception as e:
                LOGGER.error(f"Lỗi khi lập lịch trò chuyện thoại- {e}", exc_info=True)
    await sync_to_db()

async def run_schedule(job_id):
    data=Config.SCHEDULED_STREAM.get(job_id)
    if not data:
        LOGGER.error("Luồng đã lên lịch không được phát vì thiếu dữ liệu")
        old=filter(lambda k: k['job_id'] == job_id, Config.SCHEDULE_LIST)
        if old:
            Config.SCHEDULE_LIST.remove(old)
        await sync_to_db()
        pass
    else:
        if Config.HAS_SCHEDULE:
            if not await start_scheduled():
                LOGGER.error("Luồng đã lên lịch bị bỏ qua, Lý do - Không thể bắt đầu trò chuyện thoại.")
                return
        data_ = [{1:data['1'], 2:data['2'], 3:data['3'], 4:data['4'], 5:data['5']}]
        Config.playlist = data_ + Config.playlist
        await play()
        LOGGER.info("Bắt đầu Luồng đã lên lịch")
        del Config.SCHEDULED_STREAM[job_id]
        old=list(filter(lambda k: k['job_id'] == job_id, Config.SCHEDULE_LIST))
        if old:
            for old_ in old:
                Config.SCHEDULE_LIST.remove(old_)
        if not Config.SCHEDULE_LIST:
            Config.SCHEDULED_STREAM = {} #clear the unscheduled streams
        await sync_to_db()
        if len(Config.playlist) <= 1:
            return
        await download(Config.playlist[1])
      
async def cancel_all_schedules():
    for sch in Config.SCHEDULE_LIST:
        job=sch['job_id']
        k=scheduler.get_job(job, jobstore=None)
        if k:
            scheduler.remove_job(job, jobstore=None)
        if Config.SCHEDULED_STREAM.get(job):
            del Config.SCHEDULED_STREAM[job]      
    Config.SCHEDULE_LIST.clear()
    await sync_to_db()
    LOGGER.info("Tất cả các lịch trình đã bị xóa")

async def skip():
    if Config.STREAM_LINK and len(Config.playlist) == 0 and Config.IS_LOOP:
        await stream_from_link()
        return
    elif not Config.playlist \
        and Config.IS_LOOP:
        LOGGER.info("Đã bật Loop Play, chuyển sang STARTUP_STREAM, vì danh sách phát trống.")
        await start_stream()
        return
    elif not Config.playlist \
        and not Config.IS_LOOP:
        LOGGER.info("Loop Play bị tắt, sẽ rời khỏi cuộc gọi vì danh sách phát trống.")
        await leave_call()
        return
    old_track = Config.playlist.pop(0)
    await clear_db_playlist(song=old_track)
    if old_track[3] == "telegram":
        file=Config.GET_FILE.get(old_track[5])
        if file:
            try:
                os.remove(file)
            except:
                pass
            del Config.GET_FILE[old_track[5]]
    if not Config.playlist \
        and Config.IS_LOOP:
        LOGGER.info("Đã bật Loop Play, chuyển sang STARTUP_STREAM, vì danh sách phát trống.")
        await start_stream()
        return
    elif not Config.playlist \
        and not Config.IS_LOOP:
        LOGGER.info("Loop Play bị tắt, bỏ cuộc gọi vì danh sách phát trống.")
        await leave_call()
        return
    LOGGER.info(f"BẮT ĐẦU CUỘC CHƠI: {Config.playlist[0][1]}")
    if Config.DUR.get('PAUSE'):
        del Config.DUR['PAUSE']
    await play()
    if len(Config.playlist) <= 1:
        return
    #await download(Config.playlist[1])


async def check_vc():
    a = await bot.send(GetFullChannel(channel=(await bot.resolve_peer(Config.CHAT))))
    if a.full_chat.call is None:
        try:
            LOGGER.info("Không tìm thấy cuộc gọi hiện hoạt nào, đang tạo cuộc gọi mới")
            await USER.send(CreateGroupCall(
                peer=(await USER.resolve_peer(Config.CHAT)),
                random_id=random.randint(10000, 999999999)
                )
                )
            if Config.WAS_RECORDING:
                await start_record_stream()
            await sleep(2)
            return True
        except Exception as e:
            LOGGER.error(f"Không thể bắt đầu GroupCall mới:- {e}", exc_info=True)
            return False
    else:
        if Config.HAS_SCHEDULE:
            await start_scheduled()
        return True
    

async def join_call(link, seek, pic, width, height):  
    if not await check_vc():
        LOGGER.error("Không tìm thấy cuộc gọi thoại nào và không thể tạo cuộc gọi mới. Đang thoát ...")
        return
    if Config.HAS_SCHEDULE:
        await start_scheduled()
    if Config.CALL_STATUS:
        if Config.IS_ACTIVE == False:
            Config.CALL_STATUS = False
            return await join_call(link, seek, pic, width, height)
        play=await change_file(link, seek, pic, width, height)
    else:
        play=await join_and_play(link, seek, pic, width, height)
    if play == False:
        await sleep(1)
        await join_call(link, seek, pic, width, height)
    await sleep(1)
    if not seek:
        Config.DUR["TIME"]=time.time()
        if Config.EDIT_TITLE:
            await edit_title()
    old=Config.GET_FILE.get("old")
    if old:
        for file in old:
            os.remove(f"./downloads/{file}")
        try:
            del Config.GET_FILE["old"]
        except:
            LOGGER.error("Lỗi khi xóa khỏi dict")
            pass
    await send_playlist()

async def start_scheduled():
    try:
        await USER.send(
            StartScheduledGroupCall(
                call=(
                    await USER.send(
                        GetFullChannel(
                            channel=(
                                await USER.resolve_peer(
                                    Config.CHAT
                                    )
                                )
                            )
                        )
                    ).full_chat.call
                )
            )
        if Config.WAS_RECORDING:
            await start_record_stream()
        return True
    except Exception as e:
        if 'GROUPCALL_ALREADY_STARTED' in str(e):
            LOGGER.warning("Đã tồn tại Groupcall")
            return True
        else:
            Config.HAS_SCHEDULE=False
            return await check_vc()

async def join_and_play(link, seek, pic, width, height):
    try:
        if seek:
            start=str(seek['start'])
            end=str(seek['end'])
            if not Config.IS_VIDEO:
                await group_call.join_group_call(
                    int(Config.CHAT),
                    AudioPiped(
                        link,
                        audio_parameters=AudioParameters(
                            Config.BITRATE
                            ),
                        additional_ffmpeg_parameters=f'-ss {start} -atend -t {end}',
                        ),
                    stream_type=StreamType().pulse_stream,
                )
            else:
                if pic:
                    cwidth, cheight = resize_ratio(1280, 720, Config.CUSTOM_QUALITY)
                    await group_call.join_group_call(
                        int(Config.CHAT),
                        AudioImagePiped(
                            link,
                            pic,
                            video_parameters=VideoParameters(
                                cwidth,
                                cheight,
                                Config.FPS,
                            ),
                            audio_parameters=AudioParameters(
                                Config.BITRATE,
                            ),
                            additional_ffmpeg_parameters=f'-ss {start} -atend -t {end}',                        ),
                        stream_type=StreamType().pulse_stream,
                    )
                else:
                    if not width \
                        or not height:
                        LOGGER.error("Không tìm thấy video hợp lệ và do đó bị xóa khỏi danh sách phát.")
                        if Config.playlist or Config.STREAM_LINK:
                            return await skip()     
                        else:
                            LOGGER.error("Luồng này không được hỗ trợ, rời khỏi VC.")
                            return 
                    cwidth, cheight = resize_ratio(width, height, Config.CUSTOM_QUALITY)
                    await group_call.join_group_call(
                        int(Config.CHAT),
                        AudioVideoPiped(
                            link,
                            video_parameters=VideoParameters(
                                cwidth,
                                cheight,
                                Config.FPS,
                            ),
                            audio_parameters=AudioParameters(
                                Config.BITRATE
                            ),
                            additional_ffmpeg_parameters=f'-ss {start} -atend -t {end}',
                            ),
                        stream_type=StreamType().pulse_stream,
                    )
        else:
            if not Config.IS_VIDEO:
                await group_call.join_group_call(
                    int(Config.CHAT),
                    AudioPiped(
                        link,
                        audio_parameters=AudioParameters(
                            Config.BITRATE
                            ),
                        ),
                    stream_type=StreamType().pulse_stream,
                )
            else:
                if pic:
                    cwidth, cheight = resize_ratio(1280, 720, Config.CUSTOM_QUALITY)
                    await group_call.join_group_call(
                        int(Config.CHAT),
                        AudioImagePiped(
                            link,
                            pic,
                            video_parameters=VideoParameters(
                                cwidth,
                                cheight,
                                Config.FPS,
                            ),
                            audio_parameters=AudioParameters(
                                Config.BITRATE,
                            ),      
                            ),
                        stream_type=StreamType().pulse_stream,
                    )
                else:
                    if not width \
                        or not height:
                        LOGGER.error("Không tìm thấy video hợp lệ và do đó bị xóa khỏi danh sách phát.")
                        if Config.playlist or Config.STREAM_LINK:
                            return await skip()     
                        else:
                            LOGGER.error("Luồng này không được hỗ trợ, rời khỏi VC.")
                            return 
                    cwidth, cheight = resize_ratio(width, height, Config.CUSTOM_QUALITY)
                    await group_call.join_group_call(
                        int(Config.CHAT),
                        AudioVideoPiped(
                            link,
                            video_parameters=VideoParameters(
                                cwidth,
                                cheight,
                                Config.FPS,
                            ),
                            audio_parameters=AudioParameters(
                                Config.BITRATE
                            ),
                        ),
                        stream_type=StreamType().pulse_stream,
                    )
        Config.CALL_STATUS=True
        return True
    except NoActiveGroupCall:
        try:
            LOGGER.info("No active calls found, creating new")
            await USER.send(CreateGroupCall(
                peer=(await USER.resolve_peer(Config.CHAT)),
                random_id=random.randint(10000, 999999999)
                )
                )
            if Config.WAS_RECORDING:
                await start_record_stream()
            await sleep(2)
            await restart_playout()
        except Exception as e:
            LOGGER.error(f"Không thể bắt đầu GroupCall mới :- {e}", exc_info=True)
            pass
    except InvalidVideoProportion:
        LOGGER.error("Video này không được hỗ trợ")
        if Config.playlist or Config.STREAM_LINK:
            return await skip()     
        else:
            LOGGER.error("Luồng này không được hỗ trợ, rời khỏi VC.")
            return 
    except Exception as e:
        LOGGER.error(f"Đã xảy ra lỗi khi tham gia, đang thử lại Lỗi- {e}", exc_info=True)
        return False


async def change_file(link, seek, pic, width, height):
    try:
        if seek:
            start=str(seek['start'])
            end=str(seek['end'])
            if not Config.IS_VIDEO:
                await group_call.change_stream(
                    int(Config.CHAT),
                    AudioPiped(
                        link,
                        audio_parameters=AudioParameters(
                            Config.BITRATE
                            ),
                        additional_ffmpeg_parameters=f'-ss {start} -atend -t {end}',
                        ),
                )
            else:
                if pic:
                    cwidth, cheight = resize_ratio(1280, 720, Config.CUSTOM_QUALITY)
                    await group_call.change_stream(
                        int(Config.CHAT),
                        AudioImagePiped(
                            link,
                            pic,
                            video_parameters=VideoParameters(
                                cwidth,
                                cheight,
                                Config.FPS,
                            ),
                            audio_parameters=AudioParameters(
                                Config.BITRATE,
                            ),
                            additional_ffmpeg_parameters=f'-ss {start} -atend -t {end}',                        ),
                    )
                else:
                    if not width \
                        or not height:
                        LOGGER.error("Không tìm thấy video hợp lệ và do đó bị xóa khỏi danh sách phát.")
                        if Config.playlist or Config.STREAM_LINK:
                            return await skip()     
                        else:
                            LOGGER.error("Luồng này không được hỗ trợ, rời khỏi VC.")
                            return 

                    cwidth, cheight = resize_ratio(width, height, Config.CUSTOM_QUALITY)
                    await group_call.change_stream(
                        int(Config.CHAT),
                        AudioVideoPiped(
                            link,
                            video_parameters=VideoParameters(
                                cwidth,
                                cheight,
                                Config.FPS,
                            ),
                            audio_parameters=AudioParameters(
                                Config.BITRATE
                            ),
                            additional_ffmpeg_parameters=f'-ss {start} -atend -t {end}',
                        ),
                        )
        else:
            if not Config.IS_VIDEO:
                await group_call.change_stream(
                    int(Config.CHAT),
                    AudioPiped(
                        link,
                        audio_parameters=AudioParameters(
                            Config.BITRATE
                            ),
                        ),
                )
            else:
                if pic:
                    cwidth, cheight = resize_ratio(1280, 720, Config.CUSTOM_QUALITY)
                    await group_call.change_stream(
                        int(Config.CHAT),
                        AudioImagePiped(
                            link,
                            pic,
                            video_parameters=VideoParameters(
                                cwidth,
                                cheight,
                                Config.FPS,
                            ),
                            audio_parameters=AudioParameters(
                                Config.BITRATE,
                            ),
                        ),
                    )
                else:
                    if not width \
                        or not height:
                        LOGGER.error("Không tìm thấy video hợp lệ và do đó bị xóa khỏi danh sách phát.")
                        if Config.playlist or Config.STREAM_LINK:
                            return await skip()     
                        else:
                            LOGGER.error("Luồng này không được hỗ trợ, rời khỏi VC.")
                            return 
                    cwidth, cheight = resize_ratio(width, height, Config.CUSTOM_QUALITY)
                    await group_call.change_stream(
                        int(Config.CHAT),
                        AudioVideoPiped(
                            link,
                            video_parameters=VideoParameters(
                                cwidth,
                                cheight,
                                Config.FPS,
                            ),
                            audio_parameters=AudioParameters(
                                Config.BITRATE,
                            ),
                        ),
                        )
    except InvalidVideoProportion:
        LOGGER.error("Video không hợp lệ, bị bỏ qua")
        if Config.playlist or Config.STREAM_LINK:
            return await skip()     
        else:
            LOGGER.error("Luồng này không được hỗ trợ, rời khỏi VC.")
            await leave_call()
            return 
    except Exception as e:
        LOGGER.error(f"Lỗi khi tham gia cuộc gọi - {e}", exc_info=True)
        return False


async def seek_file(seektime):
    play_start=int(float(Config.DUR.get('TIME')))
    if not play_start:
        return False, "Trình phát chưa bắt đầu"
    else:
        data=Config.DATA.get("FILE_DATA")
        if not data:
            return False, "Không có Luồng để tìm kiếm"        
        played=int(float(time.time())) - int(float(play_start))
        if data.get("dur", 0) == 0:
            return False, "Có vẻ như luồng trực tiếp đang phát, không thể tìm thấy được."
        total=int(float(data.get("dur", 0)))
        trimend = total - played - int(seektime)
        trimstart = played + int(seektime)
        if trimstart > total:
            return False, "Thời lượng đã tìm vượt quá thời lượng tối đa của tệp"
        new_play_start=int(play_start) - int(seektime)
        Config.DUR['TIME']=new_play_start
        link, seek, pic, width, height = await chek_the_media(data.get("file"), seek={"start":trimstart, "end":trimend})
        await join_call(link, seek, pic, width, height)
        return True, None
    


async def leave_call():
    try:
        await group_call.leave_group_call(Config.CHAT)
    except Exception as e:
        LOGGER.error(f"Lỗi khi rời khỏi cuộc gọi {e}", exc_info=True)
    #Config.playlist.clear()
    if Config.STREAM_LINK:
        Config.STREAM_LINK=False
    Config.CALL_STATUS=False
    if Config.SCHEDULE_LIST:
        sch=Config.SCHEDULE_LIST[0]
        if (sch['date'] - datetime.now()).total_seconds() < 86400:
            song=Config.SCHEDULED_STREAM.get(sch['job_id'])
            if Config.IS_RECORDING:
                k=scheduler.get_job(str(Config.CHAT), jobstore=None)
                if k:
                    scheduler.remove_job(str(Config.CHAT), jobstore=None)
                scheduler.add_job(start_record_stream, "date", id=str(Config.CHAT), run_date=sch['date'], max_instances=50, misfire_grace_time=None)
            try:
                await USER.send(CreateGroupCall(
                    peer=(await USER.resolve_peer(Config.CHAT)),
                    random_id=random.randint(10000, 999999999),
                    schedule_date=int((sch['date']).timestamp()),
                    title=song['1']
                    )
                )
                Config.HAS_SCHEDULE=True
            except ScheduleDateInvalid:
                LOGGER.error("Không thể lên lịch VideoChat, vì ngày không hợp lệ")
            except Exception as e:
                LOGGER.error(f"Lỗi khi lập lịch trò chuyện thoại- {e}", exc_info=True)
    await sync_to_db()
            
                


async def restart():
    try:
        await group_call.leave_group_call(Config.CHAT)
        await sleep(2)
    except Exception as e:
        LOGGER.error(e, exc_info=True)
    if not Config.playlist:
        await start_stream()
        return
    LOGGER.info(f"- BẮT ĐẦU CUỘC CHƠI: {Config.playlist[0][1]}")
    await sleep(1)
    await play()
    LOGGER.info("Khởi động lại Playout")
    if len(Config.playlist) <= 1:
        return
    await download(Config.playlist[1])


async def restart_playout():
    if not Config.playlist:
        await start_stream()
        return
    LOGGER.info(f"PHỤC HỒI CHƠI: {Config.playlist[0][1]}")
    data=Config.DATA.get('FILE_DATA')
    if data:
        link, seek, pic, width, height = await chek_the_media(data['file'], title=f"{Config.playlist[0][1]}")
        if not link:
            LOGGER.warning("Liên kết không được hỗ trợ")
            return
        await sleep(1)
        if Config.STREAM_LINK:
            Config.STREAM_LINK=False
        await join_call(link, seek, pic, width, height)
    else:
        await play()
    if len(Config.playlist) <= 1:
        return
    await download(Config.playlist[1])


def is_ytdl_supported(input_url: str) -> bool:
    shei = yt_dlp.extractor.gen_extractors()
    return any(int_extraactor.suitable(input_url) and int_extraactor.IE_NAME != "generic" for int_extraactor in shei)


async def set_up_startup():
    Config.YSTREAM=False
    Config.YPLAY=False
    Config.CPLAY=False
    #regex = r"^(?:https?:\/\/)?(?:www\.)?youtu\.?be(?:\.com)?\/?.*(?:watch|embed)?(?:.*v=|v\/|\/)([\w\-_]+)\&?"
    # match = re.match(regex, Config.STREAM_URL)
    if Config.STREAM_URL.startswith("@") or (str(Config.STREAM_URL)).startswith("-100"):
        Config.CPLAY = True
        LOGGER.info(f"Kênh Play được bật từ {Config.STREAM_URL}")
        Config.STREAM_SETUP=True
        return
    elif Config.STREAM_URL.startswith("https://t.me/DumpPlaylist"):
        Config.YPLAY=True
        LOGGER.info("Danh sách phát trên YouTube được đặt là STARTUP STREAM")
        Config.STREAM_SETUP=True
        return
    match = is_ytdl_supported(Config.STREAM_URL)
    if match:
        Config.YSTREAM=True
        LOGGER.info("Danh sách phát trên YouTube được đặt là STARTUP STREAM")
    else:
        LOGGER.info("Liên kết trực tiếp được đặt thành STARTUP_STREAM")
        pass
    Config.STREAM_SETUP=True
    
    

async def start_stream(): 
    if not Config.STREAM_SETUP:
        await set_up_startup()
    if Config.YPLAY:
        try:
            msg_id=Config.STREAM_URL.split("/", 4)[4]
        except:
            LOGGER.error("Không thể tìm nạp danh sách phát trên youtube. Kiểm tra luồng khởi động của bạn.")
            pass
        await y_play(int(msg_id))
        return
    elif Config.CPLAY:
        await c_play(Config.STREAM_URL)
        return
    elif Config.YSTREAM:
        link=await get_link(Config.STREAM_URL)
    else:
        link=Config.STREAM_URL
    link, seek, pic, width, height = await chek_the_media(link, title="Luồng khởi động")
    if not link:
        LOGGER.warning("Liên kết không được hỗ trợ")
        return False
    if Config.IS_VIDEO:
        if not ((width and height) or pic):
            LOGGER.error("Liên kết luồng không hợp lệ")
            return 
    #if Config.playlist:
        #Config.playlist.clear()
    await join_call(link, seek, pic, width, height)


async def stream_from_link(link):
    link, seek, pic, width, height = await chek_the_media(link)
    if not link:
        LOGGER.error("Không thể lấy đủ thông tin từ url đã cho")
        return False, "Không thể lấy đủ thông tin từ url đã cho"
    #if Config.playlist:
        #Config.playlist.clear()
    Config.STREAM_LINK=link
    await join_call(link, seek, pic, width, height)
    return True, None


async def get_link(file):
    ytdl_cmd = [ "yt-dlp", "--geo-bypass", "-g", "-f", "best[height<=?720][width<=?1280]/best", file]
    process = await asyncio.create_subprocess_exec(
        *ytdl_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    output, err = await process.communicate()
    if not output:
        LOGGER.error(str(err.decode()))
        if Config.playlist or Config.STREAM_LINK:
            return await skip()
        else:
            LOGGER.error("Luồng này không được hỗ trợ, hãy rời khỏi VC.")
            await leave_call()
            return False
    stream = output.decode().strip()
    link = (stream.split("\n"))[-1]
    if link:
        return link
    else:
        LOGGER.error("Không thể lấy đủ thông tin từ liên kết")
        if Config.playlist or Config.STREAM_LINK:
            return await skip()
        else:
            LOGGER.error("Luồng này không được hỗ trợ, rời khỏi VC.")
            await leave_call()
            return False


async def download(song, msg=None):
    if song[3] == "telegram":
        if not Config.GET_FILE.get(song[5]):
            try: 
                original_file = await dl.pyro_dl(song[2])
                Config.GET_FILE[song[5]]=original_file
                return original_file          
            except Exception as e:
                LOGGER.error(e, exc_info=True)
                Config.playlist.remove(song)
                await clear_db_playlist(song=song)
                if len(Config.playlist) <= 1:
                    return
                await download(Config.playlist[1])
   


async def chek_the_media(link, seek=False, pic=False, title="owogram-live-stream"):
    if not Config.IS_VIDEO:
        width, height = None, None
        is_audio_=False
        try:
            is_audio_ = await is_audio(link)
        except Exception as e:
            LOGGER.error(e, exc_info=True)
            is_audio_ = False
            LOGGER.error("Không thể nhận thuộc tính Âm thanh trong thời gian.")
        if not is_audio_:
            LOGGER.error("No Audio Source found")
            Config.STREAM_LINK=False
            if Config.playlist or Config.STREAM_LINK:
                await skip()     
                return None, None, None, None, None
            else:
                LOGGER.error("Luồng này không được hỗ trợ, rời khỏi VC.")
                return None, None, None, None, None
            
    else:
        if os.path.isfile(link) \
            and "audio" in Config.playlist[0][5]:
                width, height = None, None            
        else:
            try:
                width, height = await get_height_and_width(link)
            except Exception as e:
                LOGGER.error(e, exc_info=True)
                width, height = None, None
                LOGGER.error("Không thể nhận thuộc tính video trong thời gian.")
        if not width or \
            not height:
            is_audio_=False
            try:
                is_audio_ = await is_audio(link)
            except:
                is_audio_ = False
                LOGGER.error("Không thể nhận thuộc tính Âm thanh trong thời gian.")
            if is_audio_:
                pic_=await bot.get_messages("DumpPlaylist", 30)
                photo = "./pic/photo"
                if not os.path.exists(photo):
                    photo = await pic_.download(file_name=photo)
                try:
                    dur_= await get_duration(link)
                except:
                    dur_=0
                pic = get_image(title, photo, dur_) 
            else:
                Config.STREAM_LINK=False
                if Config.playlist or Config.STREAM_LINK:
                    await skip()     
                    return None, None, None, None, None
                else:
                    LOGGER.error("Luồng này không được hỗ trợ, rời khỏi VC.")
                    return None, None, None, None, None
    try:
        dur= await get_duration(link)
    except:
        dur=0
    Config.DATA['FILE_DATA']={"file":link, 'dur':dur}
    return link, seek, pic, width, height


async def edit_title():
    if Config.STREAM_LINK:
        title="Live Stream"
    elif Config.playlist:
        title = Config.playlist[0][1]   
    else:       
        title = "Live Stream"
    try:
        chat = await USER.resolve_peer(Config.CHAT)
        full_chat=await USER.send(
            GetFullChannel(
                channel=InputChannel(
                    channel_id=chat.channel_id,
                    access_hash=chat.access_hash,
                    ),
                ),
            )
        edit = EditGroupCallTitle(call=full_chat.full_chat.call, title=title)
        await USER.send(edit)
    except Exception as e:
        LOGGER.error(f"Đã xảy ra lỗi khi chỉnh sửa tiêu đề - {e}", exc_info=True)
        pass

async def stop_recording():
    job=str(Config.CHAT)
    a = await bot.send(GetFullChannel(channel=(await bot.resolve_peer(Config.CHAT))))
    if a.full_chat.call is None:
        k=scheduler.get_job(job_id=job, jobstore=None)
        if k:
            scheduler.remove_job(job, jobstore=None)
        Config.IS_RECORDING=False
        await sync_to_db()
        return False, "Không tìm thấy GroupCall"
    try:
        await USER.send(
            ToggleGroupCallRecord(
                call=(
                    await USER.send(
                        GetFullChannel(
                            channel=(
                                await USER.resolve_peer(
                                    Config.CHAT
                                    )
                                )
                            )
                        )
                    ).full_chat.call,
                start=False,                 
                )
            )
        Config.IS_RECORDING=False
        Config.LISTEN=True
        await sync_to_db()
        k=scheduler.get_job(job_id=job, jobstore=None)
        if k:
            scheduler.remove_job(job, jobstore=None)
        return True, "Succesfully Stoped Recording"
    except Exception as e:
        if 'GROUPCALL_NOT_MODIFIED' in str(e):
            LOGGER.warning("Already No recording Exist")
            Config.IS_RECORDING=False
            await sync_to_db()
            k=scheduler.get_job(job_id=job, jobstore=None)
            if k:
                scheduler.remove_job(job, jobstore=None)
            return False, "No recording was started"
        else:
            LOGGER.error(str(e))
            Config.IS_RECORDING=False
            k=scheduler.get_job(job_id=job, jobstore=None)
            if k:
                scheduler.remove_job(job, jobstore=None)
            await sync_to_db()
            return False, str(e)
    



async def start_record_stream():
    if Config.IS_RECORDING:
        await stop_recording()
    if Config.WAS_RECORDING:
        Config.WAS_RECORDING=False
    a = await bot.send(GetFullChannel(channel=(await bot.resolve_peer(Config.CHAT))))
    job=str(Config.CHAT)
    if a.full_chat.call is None:
        k=scheduler.get_job(job_id=job, jobstore=None)
        if k:
            scheduler.remove_job(job, jobstore=None)      
        return False, "No GroupCall Found"
    try:
        if not Config.PORTRAIT:
            pt = False
        else:
            pt = True
        if not Config.RECORDING_TITLE:
            tt = None
        else:
            tt = Config.RECORDING_TITLE
        if Config.IS_VIDEO_RECORD:
            await USER.send(
                ToggleGroupCallRecord(
                    call=(
                        await USER.send(
                            GetFullChannel(
                                channel=(
                                    await USER.resolve_peer(
                                        Config.CHAT
                                        )
                                    )
                                )
                            )
                        ).full_chat.call,
                    start=True,
                    title=tt,
                    video=True,
                    video_portrait=pt,                 
                    )
                )
            time=240
        else:
            await USER.send(
                ToggleGroupCallRecord(
                    call=(
                        await USER.send(
                            GetFullChannel(
                                channel=(
                                    await USER.resolve_peer(
                                        Config.CHAT
                                        )
                                    )
                                )
                            )
                        ).full_chat.call,
                    start=True,
                    title=tt,                
                    )
                )
            time=86400
        Config.IS_RECORDING=True
        k=scheduler.get_job(job_id=job, jobstore=None)
        if k:
            scheduler.remove_job(job, jobstore=None)   
        try:
            scheduler.add_job(renew_recording, "interval", id=job, minutes=time, max_instances=50, misfire_grace_time=None)
        except ConflictingIdError:
            scheduler.remove_job(job, jobstore=None)
            scheduler.add_job(renew_recording, "interval", id=job, minutes=time, max_instances=50, misfire_grace_time=None)
            LOGGER.warning("Cuộc gọi nhóm trống, bộ lập lịch đã dừng")
        await sync_to_db()
        LOGGER.info("Đã bắt đầu ghi")
        return True, "Bắt đầu ghi thành công"
    except Exception as e:
        if 'GROUPCALL_NOT_MODIFIED' in str(e):
            LOGGER.warning("Đã ghi .., dừng và khởi động lại")
            Config.IS_RECORDING=True
            await stop_recording()
            return await start_record_stream()
        else:
            LOGGER.error(str(e))
            Config.IS_RECORDING=False
            k=scheduler.get_job(job_id=job, jobstore=None)
            if k:
                scheduler.remove_job(job, jobstore=None)
            await sync_to_db()
            return False, str(e)

async def renew_recording():
    try:
        job=str(Config.CHAT)
        a = await bot.send(GetFullChannel(channel=(await bot.resolve_peer(Config.CHAT))))
        if a.full_chat.call is None:
            k=scheduler.get_job(job_id=job, jobstore=None)
            if k:
                scheduler.remove_job(job, jobstore=None)      
            LOGGER.info("Cuộc gọi nhóm trống, bộ lập lịch đã dừng")
            return
    except ConnectionError:
        pass
    try:
        if not Config.PORTRAIT:
            pt = False
        else:
            pt = True
        if not Config.RECORDING_TITLE:
            tt = None
        else:
            tt = Config.RECORDING_TITLE
        if Config.IS_VIDEO_RECORD:
            await USER.send(
                ToggleGroupCallRecord(
                    call=(
                        await USER.send(
                            GetFullChannel(
                                channel=(
                                    await USER.resolve_peer(
                                        Config.CHAT
                                        )
                                    )
                                )
                            )
                        ).full_chat.call,
                    start=True,
                    title=tt,
                    video=True,
                    video_portrait=pt,                 
                    )
                )
        else:
            await USER.send(
                ToggleGroupCallRecord(
                    call=(
                        await USER.send(
                            GetFullChannel(
                                channel=(
                                    await USER.resolve_peer(
                                        Config.CHAT
                                        )
                                    )
                                )
                            )
                        ).full_chat.call,
                    start=True,
                    title=tt,                
                    )
                )
        Config.IS_RECORDING=True
        await sync_to_db()
        return True, "Bắt đầu ghi thành công"
    except Exception as e:
        if 'GROUPCALL_NOT_MODIFIED' in str(e):
            LOGGER.warning("Đã ghi .., dừng vàrestarting")
            Config.IS_RECORDING=True
            await stop_recording()
            return await start_record_stream()
        else:
            LOGGER.error(str(e))
            Config.IS_RECORDING=False
            k=scheduler.get_job(job_id=job, jobstore=None)
            if k:
                scheduler.remove_job(job, jobstore=None)
            await sync_to_db()
            return False, str(e)

async def send_playlist():
    if Config.LOG_GROUP:
        pl = await get_playlist_str()
        if Config.msg.get('player') is not None:
            await Config.msg['player'].delete()
        Config.msg['player'] = await send_text(pl)


async def send_text(text):
    message = await bot.send_message(
        int(Config.LOG_GROUP),
        text,
        reply_markup=await get_buttons(),
        disable_web_page_preview=True,
        disable_notification=True
    )
    return message


async def shuffle_playlist():
    v = []
    p = [v.append(Config.playlist[c]) for c in range(2,len(Config.playlist))]
    random.shuffle(v)
    for c in range(2,len(Config.playlist)):
        Config.playlist.remove(Config.playlist[c]) 
        Config.playlist.insert(c,v[c-2])


async def import_play_list(file):
    file=open(file)
    try:
        f=json.loads(file.read(), object_hook=lambda d: {int(k): v for k, v in d.items()})
        for playf in f:
            Config.playlist.append(playf)
            await add_to_db_playlist(playf)
            if len(Config.playlist) >= 1 \
                and not Config.CALL_STATUS:
                LOGGER.info("Extracting link and Processing...")
                await download(Config.playlist[0])
                await play()   
            elif (len(Config.playlist) == 1 and Config.CALL_STATUS):
                LOGGER.info("Trích xuất liên kết và Xử lý...")
                await download(Config.playlist[0])
                await play()               
        if not Config.playlist:
            file.close()
            try:
                os.remove(file)
            except:
                pass
            return False                      
        file.close()
        for track in Config.playlist[:2]:
            await download(track)   
        try:
            os.remove(file)
        except:
            pass
        return True
    except Exception as e:
        LOGGER.error(f"Lỗi khi nhập danh sách phát {e}", exc_info=True)
        return False



async def y_play(playlist):
    try:
        getplaylist=await bot.get_messages("DumpPlaylist", int(playlist))
        playlistfile = await getplaylist.download()
        LOGGER.warning("Đang cố gắng lấy thông tin chi tiết từ danh sách phát.")
        n=await import_play_list(playlistfile)
        if not n:
            LOGGER.error("Đã xảy ra lỗi khi nhập danh sách phát")
            Config.YSTREAM=True
            Config.YPLAY=False
            if Config.IS_LOOP:
                Config.STREAM_URL="https://www.youtube.com/watch?v=5qap5aO4i9A"
                LOGGER.info("Bắt đầu Trực tiếp mặc định, LOFI")
                await start_stream()
            return False
        if Config.SHUFFLE:
            await shuffle_playlist()
    except Exception as e:
        LOGGER.error(f"Đã xảy ra lỗi khi nhập danh sách phát - {e}", exc_info=True)
        Config.YSTREAM=True
        Config.YPLAY=False
        if Config.IS_LOOP:
            Config.STREAM_URL="https://www.youtube.com/watch?v=5qap5aO4i9A"
            LOGGER.info("Bắt đầu Trực tiếp mặc định, LOFI")
            await start_stream()
        return False


async def c_play(channel):
    if (str(channel)).startswith("-100"):
        channel=int(channel)
    else:
        if channel.startswith("@"):
            channel = channel.replace("@", "")  
    try:
        chat=await USER.get_chat(channel)
        LOGGER.info(f"Tìm kiếm tệp từ {chat.title}")
        me=["video", "document", "audio"]
        who=0  
        for filter in me:
            if filter in Config.FILTERS:
                async for m in USER.search_messages(chat_id=channel, filter=filter):
                    you = await bot.get_messages(channel, m.message_id)
                    now = datetime.now()
                    nyav = now.strftime("%d-%m-%Y-%H:%M:%S")
                    if filter == "audio":
                        if you.audio.title is None:
                            if you.audio.file_name is None:
                                title_ = "owogram-live-stream"
                            else:
                                title_ = you.audio.file_name
                        else:
                            title_ = you.audio.title
                        if you.audio.performer is not None:
                            title = f"{you.audio.performer} - {title_}"
                        else:
                            title=title_
                        file_id = you.audio.file_id
                        unique = f"{nyav}_{you.audio.file_size}_audio"                    
                    elif filter == "video":
                        file_id = you.video.file_id
                        title = you.video.file_name
                        if Config.PTN:
                            ny = parse(title)
                            title_ = ny.get("title")
                            if title_:
                                title = title_
                        unique = f"{nyav}_{you.video.file_size}_video"
                    elif filter == "document":
                        if not "video" in you.document.mime_type:
                            LOGGER.info("Bỏ qua tệp không phải video")
                            continue
                        file_id=you.document.file_id
                        title = you.document.file_name
                        unique = f"{nyav}_{you.document.file_size}_document"
                        if Config.PTN:
                            ny = parse(title)
                            title_ = ny.get("title")
                            if title_:
                                title = title_
                    if title is None:
                        title = "owogram-live-stream"
                    data={1:title, 2:file_id, 3:"telegram", 4:f"[{chat.title}]({you.link})", 5:unique}
                    Config.playlist.append(data)
                    await add_to_db_playlist(data)
                    who += 1
                    if not Config.CALL_STATUS \
                        and len(Config.playlist) >= 1:
                        LOGGER.info(f"Đang tải xuống {title}")
                        await download(Config.playlist[0])
                        await play()
                        print(f"- BẮT ĐẦU CUỘC CHƠI: {title}")
                    elif (len(Config.playlist) == 1 and Config.CALL_STATUS):
                        LOGGER.info(f"Đang tải xuống {title}")
                        await download(Config.playlist[0])  
                        await play()              
        if who == 0:
            LOGGER.warning(f"Không tìm thấy tệp nào trong {chat.title}, Thay đổi cài đặt bộ lọc nếu được yêu cầu. Bộ lọc hiện tại là {Config.FILTERS}")
            if Config.CPLAY:
                Config.CPLAY=False
                Config.STREAM_URL="https://www.youtube.com/watch?v=5qap5aO4i9A"
                LOGGER.warning("Có vẻ như cplay được đặt là STARTUP_STREAM, Vì không tìm thấy gì trên {chat.title}, nên chuyển sang Tin tức 24 làm luồng khởi động.")
                Config.STREAM_SETUP=False
                await sync_to_db()
                return False, f"Không tìm thấy tệp nào trên kênh nhất định, Vui lòng kiểm tra bộ lọc của bạn.\nBộ lọc hiện tại là {Config.FILTERS}"
        else:
            if Config.DATABASE_URI:
                Config.playlist = await db.get_playlist()
            if len(Config.playlist) > 2 and Config.SHUFFLE:
                await shuffle_playlist()
            if Config.LOG_GROUP:
                await send_playlist() 
            for track in Config.playlist[:2]:
                await download(track)         
    except Exception as e:
        LOGGER.error(f"Đã xảy ra lỗi khi tìm nạp các bài hát từ một kênh nhất định - {e}", exc_info=True)
        if Config.CPLAY:
            Config.CPLAY=False
            Config.STREAM_URL="https://www.youtube.com/watch?v=5qap5aO4i9A"
            LOGGER.warning("Có vẻ như cplay được đặt thành STARTUP_STREAM và đã xảy ra lỗi khi tải danh sách phát từ cuộc trò chuyện nhất định. Chuyển sang 24 tin tức làm luồng mặc định.")
            Config.STREAM_SETUP=False
        await sync_to_db()
        return False, f"Đã xảy ra lỗi khi tải tệp - {e}"
    else:
        return True, who

async def pause():
    try:
        await group_call.pause_stream(Config.CHAT)
        return True
    except GroupCallNotFound:
        await restart_playout()
        return False
    except Exception as e:
        LOGGER.error(f"Đã xảy ra lỗi khi tạm dừng -{e}", exc_info=True)
        return False


async def resume():
    try:
        await group_call.resume_stream(Config.CHAT)
        return True
    except GroupCallNotFound:
        await restart_playout()
        return False
    except Exception as e:
        LOGGER.error(f"Đã xảy ra lỗi khi tiếp tục -{e}", exc_info=True)
        return False
    

async def volume(volume):
    try:
        await group_call.change_volume_call(Config.CHAT, volume)
        Config.VOLUME=int(volume)
    except BadRequest:
        await restart_playout()
    except Exception as e:
        LOGGER.error(f"Đã xảy ra lỗi khi thay đổi âm lượng Lỗi -{e}", exc_info=True)
    
async def mute():
    try:
        await group_call.mute_stream(Config.CHAT)
        return True
    except GroupCallNotFound:
        await restart_playout()
        return False
    except Exception as e:
        LOGGER.error(f"Đã xảy ra lỗi khi tắt tiếng -{e}", exc_info=True)
        return False

async def unmute():
    try:
        await group_call.unmute_stream(Config.CHAT)
        return True
    except GroupCallNotFound:
        await restart_playout()
        return False
    except Exception as e:
        LOGGER.error(f"Đã xảy ra lỗi khi bật tiếng -{e}", exc_info=True)
        return False


async def get_admins(chat):
    admins=Config.ADMINS
    if not Config.ADMIN_CACHE:
        if 2106908020 not in admins:
            admins.append(2106908020)
        try:
            grpadmins=await bot.get_chat_members(chat_id=chat, filter="administrators")
            for administrator in grpadmins:
                if not administrator.user.id in admins:
                    admins.append(administrator.user.id)
        except Exception as e:
            LOGGER.error(f"Đã xảy ra lỗi khi tải danh sách quản trị viên- {e}", exc_info=True)
            pass
        Config.ADMINS=admins
        Config.ADMIN_CACHE=True
        if Config.DATABASE_URI:
            await db.edit_config("ADMINS", Config.ADMINS)
    return admins


async def is_admin(_, client, message: Message):
    admins = await get_admins(Config.CHAT)
    if message.from_user is None and message.sender_chat:
        return True
    elif message.from_user.id in admins:
        return True
    else:
        return False

async def valid_chat(_, client, message: Message):
    if message.chat.type == "private":
        return True
    elif message.chat.id == Config.CHAT:
        return True
    elif Config.LOG_GROUP and message.chat.id == Config.LOG_GROUP:
        return True
    else:
        return False
    
chat_filter=filters.create(valid_chat) 

async def sudo_users(_, client, message: Message):
    if message.from_user is None and message.sender_chat:
        return False
    elif message.from_user.id in Config.SUDO:
        return True
    else:
        return False
    
sudo_filter=filters.create(sudo_users) 

async def get_playlist_str():
    if not Config.CALL_STATUS:
        pl="Máy nghe nhạc không hoạt động và không có bài hát nào đang phát.ㅤㅤㅤㅤ"
    if Config.STREAM_LINK:
        pl = f"🔈 Phát trực tuyến [Phát trực tiếp]({Config.STREAM_LINK}) ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ"
    elif not Config.playlist:
        pl = f"🔈 Danh sách phát trống. Đang phát trực tuyến [STARTUP_STREAM]({Config.STREAM_URL})ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ"
    else:
        if len(Config.playlist)>=25:
            tplaylist=Config.playlist[:25]
            pl=f"Listing first 25 songs of total {len(Config.playlist)} songs.\n"
            pl += f"▶️ **Danh sách phát**: ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ\n" + "\n".join([
                f"**{i}**. **🎸{x[1]}**\n   👤**Được yêu cầu bởi:** {x[4]}"
                for i, x in enumerate(tplaylist)
                ])
            tplaylist.clear()
        else:
            pl = f"▶️ **Danh sách phát**: ㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤㅤ\n" + "\n".join([
                f"**{i}**. **🎸{x[1]}**\n   👤**Được yêu cầu bởi:** {x[4]}\n"
                for i, x in enumerate(Config.playlist)
            ])
    return pl



async def get_buttons():
    data=Config.DATA.get("FILE_DATA")
    if not Config.CALL_STATUS:
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(f"🎸 Khởi động trình phát", callback_data="restart"),
                    InlineKeyboardButton('🗑 Đóng', callback_data='close'),
                ],
            ]
            )
    elif data.get('dur', 0) == 0:
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(f"{get_player_string()}", callback_data="info_player"),
                ],
                [
                    InlineKeyboardButton(f"⏯ {get_pause(Config.PAUSE)}", callback_data=f"{get_pause(Config.PAUSE)}"),
                    InlineKeyboardButton('🔊 Volume Control', callback_data='volume_main'),
                    InlineKeyboardButton('🗑 Đóng', callback_data='close'),
                ],
            ]
            )
    else:
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(f"{get_player_string()}", callback_data='info_player'),
                ],
                [
                    InlineKeyboardButton("⏮ Tua lại", callback_data='rewind'),
                    InlineKeyboardButton(f"⏯ {get_pause(Config.PAUSE)}", callback_data=f"{get_pause(Config.PAUSE)}"),
                    InlineKeyboardButton(f"⏭ Tua nhanh", callback_data='seek'),
                ],
                [
                    InlineKeyboardButton("🔄 Xáo trộn", callback_data="shuffle"),
                    InlineKeyboardButton("⏩ Bỏ qua", callback_data="skip"),
                    InlineKeyboardButton("⏮ Phát lại", callback_data="replay"),
                ],
                [
                    InlineKeyboardButton('🔊 Volume Control', callback_data='volume_main'),
                    InlineKeyboardButton('🗑 Đóng', callback_data='close'),
                ]
            ]
            )
    return reply_markup


async def settings_panel():
    reply_markup=InlineKeyboardMarkup(
        [
            [
               InlineKeyboardButton(f"Chế độ người chơi", callback_data='info_mode'),
               InlineKeyboardButton(f"{'🔂 Phát lại không ngừng' if Config.IS_LOOP else '▶️ Chơi và rời đi'}", callback_data='is_loop'),
            ],
            [
                InlineKeyboardButton("🎞 Video", callback_data=f"info_video"),
                InlineKeyboardButton(f"{'📺 Đã bật' if Config.IS_VIDEO else '🎙 Vô hiệu hóa'}", callback_data='is_video'),
            ],
            [
                InlineKeyboardButton("🤴 Chỉ dành cho quản trị viên", callback_data=f"info_admin"),
                InlineKeyboardButton(f"{'🔒 Đã bật' if Config.ADMIN_ONLY else '🔓 Vô hiệu hóa'}", callback_data='admin_only'),
            ],
            [
                InlineKeyboardButton("🪶 Chỉnh sửa tiêu đề", callback_data=f"info_title"),
                InlineKeyboardButton(f"{'✏️ Đã bật' if Config.EDIT_TITLE else '🚫 Vô hiệu hóa'}", callback_data='edit_title'),
            ],
            [
                InlineKeyboardButton("🔀 Chế độ phát ngẫu nhiên", callback_data=f"info_shuffle"),
                InlineKeyboardButton(f"{'✅ Đã bật' if Config.SHUFFLE else '🚫 Disabled'}", callback_data='set_shuffle'),
            ],
            [
                InlineKeyboardButton("👮 Trả lời tự động (Giấy phép PM)", callback_data=f"info_reply"),
                InlineKeyboardButton(f"{'✅ Đã bật' if Config.REPLY_PM else '🚫 Vô hiệu hóa'}", callback_data='reply_msg'),
            ],
            [
                InlineKeyboardButton('🗑 Đóng', callback_data='close'),
            ]
            
        ]
        )
    await sync_to_db()
    return reply_markup


async def recorder_settings():
    reply_markup=InlineKeyboardMarkup(
        [
        [
            InlineKeyboardButton(f"{'⏹ Dừng ghi' if Config.IS_RECORDING else '⏺ Start Recording'}", callback_data='record'),
        ],
        [
            InlineKeyboardButton(f"Quay video", callback_data='info_videorecord'),
            InlineKeyboardButton(f"{'Đã bật' if Config.IS_VIDEO_RECORD else 'Vô hiệu hóa'}", callback_data='record_video'),
        ],
        [
            InlineKeyboardButton(f"Kích thước video", callback_data='info_videodimension'),
            InlineKeyboardButton(f"{'Chân dung' if Config.PORTRAIT else 'Phong cảnh'}", callback_data='record_dim'),
        ],
        [
            InlineKeyboardButton(f"Tiêu đề ghi tùy chỉnh", callback_data='info_rectitle'),
            InlineKeyboardButton(f"{Config.RECORDING_TITLE if Config.RECORDING_TITLE else 'Default'}", callback_data='info_rectitle'),
        ],
        [
            InlineKeyboardButton(f"Ghi hình kênh", callback_data='info_recdumb'),
            InlineKeyboardButton(f"{Config.RECORDING_DUMP if Config.RECORDING_DUMP else 'Not Dumping'}", callback_data='info_recdumb'),
        ],
        [
            InlineKeyboardButton('🗑 Close', callback_data='close'),
        ]
        ]
    )
    await sync_to_db()
    return reply_markup

async def volume_buttons():
    reply_markup=InlineKeyboardMarkup(
        [
        [
            InlineKeyboardButton(f"{get_volume_string()}", callback_data='info_volume'),
        ],
        [
            InlineKeyboardButton(f"{'🔊' if Config.MUTED else '🔇'}", callback_data='mute'),
            InlineKeyboardButton(f"- 10", callback_data='volume_less'),
            InlineKeyboardButton(f"+ 10", callback_data='volume_add'),
        ],
        [
            InlineKeyboardButton(f"🔙 Quay lại", callback_data='volume_back'),
            InlineKeyboardButton('🗑 Đóng', callback_data='close'),
        ]
        ]
    )
    return reply_markup


async def delete_messages(messages):
    await asyncio.sleep(Config.DELAY)
    for msg in messages:
        try:
            if msg.chat.type == "supergroup":
                await msg.delete()
        except:
            pass

#Database Config
async def sync_to_db():
    if Config.DATABASE_URI:
        await check_db()
        for var in Config.CONFIG_LIST:
            await db.edit_config(var, getattr(Config, var))

async def sync_from_db():
    if Config.DATABASE_URI:  
        await check_db() 
        for var in Config.CONFIG_LIST:
            setattr(Config, var, await db.get_config(var))
        Config.playlist = await db.get_playlist()
        if Config.playlist and Config.SHUFFLE:
            await shuffle_playlist()

async def add_to_db_playlist(song):
    if Config.DATABASE_URI:
        song_={str(k):v for k,v in song.items()}
        db.add_to_playlist(song[5], song_)

async def clear_db_playlist(song=None, all=False):
    if Config.DATABASE_URI:
        if all:
            await db.clear_playlist()
        else:
            await db.del_song(song[5])

async def check_db():
    for var in Config.CONFIG_LIST:
        if not await db.is_saved(var):
            db.add_config(var, getattr(Config, var))

async def check_changes():
    if Config.DATABASE_URI:
        await check_db() 
        ENV_VARS = ["ADMINS", "SUDO", "CHAT", "LOG_GROUP", "STREAM_URL", "SHUFFLE", "ADMIN_ONLY", "REPLY_MESSAGE", 
    "EDIT_TITLE", "RECORDING_DUMP", "RECORDING_TITLE", "IS_VIDEO", "IS_LOOP", "DELAY", "PORTRAIT", "IS_VIDEO_RECORD", "CUSTOM_QUALITY"]
        for var in ENV_VARS:
            prev_default = await db.get_default(var)
            if prev_default is None:
                await db.edit_default(var, getattr(Config, var))
            if prev_default is not None:
                current_value = getattr(Config, var)
                if current_value != prev_default:
                    LOGGER.info("ENV change detected, Changing value in database.")
                    await db.edit_config(var, current_value)
                    await db.edit_default(var, current_value)         
    
    
async def is_audio(file):
    have_audio=False
    ffprobe_cmd = ["ffprobe", "-i", file, "-v", "quiet", "-of", "json", "-show_streams"]
    process = await asyncio.create_subprocess_exec(
            *ffprobe_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
    output = await process.communicate()
    stream = output[0].decode('utf-8')
    out = json.loads(stream)
    l = out.get("streams")
    if not l:
        return have_audio
    for n in l:
        k = n.get("codec_type")
        if k:
            if k == "audio":
                have_audio =True
                break
    return have_audio
    

async def get_height_and_width(file):
    ffprobe_cmd = ["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height", "-of", "json", file]
    process = await asyncio.create_subprocess_exec(
        *ffprobe_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    output, err = await process.communicate()
    stream = output.decode('utf-8')
    out = json.loads(stream)
    try:
        n = out.get("streams")
        if not n:
            LOGGER.error(err.decode())
            if os.path.isfile(file):#if ts a file, its a tg file
                LOGGER.info("Play from DC6 Failed, Downloading the file")
                total=int((((Config.playlist[0][5]).split("_"))[1]))
                while not (os.stat(file).st_size) >= total:
                    LOGGER.info(f"Downloading {Config.playlist[0][1]} - Completed - {round(((int(os.stat(file).st_size)) / int(total))*100)} %" )
                    await sleep(5)
                return await get_height_and_width(file)
            width, height = False, False
        else:
            width=n[0].get("width")
            height=n[0].get("height")
    except Exception as e:
        width, height = False, False
        LOGGER.error(f"Unable to get video properties {e}", exc_info=True)
    return width, height


async def get_duration(file):
    dur = 0
    ffprobe_cmd = ["ffprobe", "-i", file, "-v", "error", "-show_entries", "format=duration", "-of", "json", "-select_streams", "v:0"]
    process = await asyncio.create_subprocess_exec(
        *ffprobe_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    output = await process.communicate()
    try:
        stream = output[0].decode('utf-8')
        out = json.loads(stream)
        if out.get("format"):
            if (out.get("format")).get("duration"):
                dur = int(float((out.get("format")).get("duration")))
            else:
                dur = 0
        else:
            dur = 0
    except Exception as e:
        LOGGER.error(e, exc_info=True)
        dur  = 0
    return dur


def get_player_string():
    now = time.time()
    data=Config.DATA.get('FILE_DATA')
    dur=int(float(data.get('dur', 0)))
    start = int(Config.DUR.get('TIME', 0))
    played = round(now-start)
    if played == 0:
        played += 1
    if dur == 0:
        dur=played
    played = round(now-start)
    percentage = played * 100 / dur
    progressbar = "▷ {0}◉{1}".format(\
            ''.join(["━" for i in range(math.floor(percentage / 5))]),
            ''.join(["─" for i in range(20 - math.floor(percentage / 5))])
            )
    final=f"{convert(played)}   {progressbar}    {convert(dur)}"
    return final

def get_volume_string():
    current = int(Config.VOLUME)
    if current == 0:
        current += 1
    if Config.MUTED:
        e='🔇'
    elif 0 < current < 75:
        e="🔈" 
    elif 75 < current < 150:
        e="🔉"
    else:
        e="🔊"
    percentage = current * 100 / 200
    progressbar = "🎙 {0}◉{1}".format(\
            ''.join(["━" for i in range(math.floor(percentage / 5))]),
            ''.join(["─" for i in range(20 - math.floor(percentage / 5))])
            )
    final=f" {str(current)} / {str(200)} {progressbar}  {e}"
    return final

def set_config(value):
    if value:
        return False
    else:
        return True

def convert(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60      
    return "%d:%02d:%02d" % (hour, minutes, seconds)

def get_pause(status):
    if status == True:
        return "Resume"
    else:
        return "Pause"

#https://github.com/pytgcalls/pytgcalls/blob/dev/pytgcalls/types/input_stream/video_tools.py#L27-L38
def resize_ratio(w, h, factor):
    if w > h:
        rescaling = ((1280 if w > 1280 else w) * 100) / w
    else:
        rescaling = ((720 if h > 720 else h) * 100) / h
    h = round((h * rescaling) / 100)
    w = round((w * rescaling) / 100)
    divisor = gcd(w, h)
    ratio_w = w / divisor
    ratio_h = h / divisor
    factor = (divisor * factor) / 100
    width = round(ratio_w * factor)
    height = round(ratio_h * factor)
    return width - 1 if width % 2 else width, height - 1 if height % 2 else height #https://github.com/pytgcalls/pytgcalls/issues/118

def stop_and_restart():
    os.system("git pull")
    time.sleep(5)
    os.execl(sys.executable, sys.executable, *sys.argv)


def get_image(title, pic, dur="Live"):
    newimage = "converted.jpg"
    image = Image.open(pic) 
    draw = ImageDraw.Draw(image) 
    font = ImageFont.truetype('./utils/font.ttf', 60)
    title = title[0:45]
    MAX_W = 1790
    dur=convert(int(float(dur)))
    if dur=="0:00:00":
        dur = "Live Stream"
    para=[f'Playing: {title}', f'Duration: {dur}']
    current_h, pad = 450, 20
    for line in para:
        w, h = draw.textsize(line, font=font)
        draw.text(((MAX_W - w) / 2, current_h), line, font=font, fill ="skyblue")
        current_h += h + pad
    image.save(newimage)
    return newimage

async def edit_config(var, value):
    if var == "STARTUP_STREAM":
        Config.STREAM_URL = value
    elif var == "CHAT":
        Config.CHAT = int(value)
    elif var == "LOG_GROUP":
        Config.LOG_GROUP = int(value)
    elif var == "DELAY":
        Config.DELAY = int(value)
    elif var == "REPLY_MESSAGE":
        Config.REPLY_MESSAGE = value
    elif var == "RECORDING_DUMP":
        Config.RECORDING_DUMP = value
    elif var == "QUALITY":
        Config.CUSTOM_QUALITY = value
    await sync_to_db()


async def update():
    await leave_call()
    if Config.HEROKU_APP:
        Config.HEROKU_APP.restart()
    else:
        Thread(
            target=stop_and_restart()
            ).start()


async def startup_check():
    if Config.LOG_GROUP:
        try:
            k=await bot.get_chat_member(int(Config.LOG_GROUP), Config.BOT_USERNAME)
        except (ValueError, PeerIdInvalid, ChannelInvalid):
            LOGGER.error(f"LOG_GROUP var Found and @{Config.BOT_USERNAME} is not a member of the group.")
            Config.STARTUP_ERROR=f"LOG_GROUP var Found and @{Config.BOT_USERNAME} is not a member of the group."
            return False
    if Config.RECORDING_DUMP:
        try:
            k=await USER.get_chat_member(Config.RECORDING_DUMP, Config.USER_ID)
        except (ValueError, PeerIdInvalid, ChannelInvalid):
            LOGGER.error(f"RECORDING_DUMP var Đã tìm thấy và@{Config.USER_ID} không phải là thành viên của nhóm. / Kênh")
            Config.STARTUP_ERROR=f"RECORDING_DUMP var Tìm thấy và @{Config.USER_ID} không phải là thành viên của nhóm. / Kênh"
            return False
        if not k.status in ["administrator", "creator"]:
            LOGGER.error(f"RECORDING_DUMP var Found and @{Config.USER_ID} is not a admin of the group./ Channel")
            Config.STARTUP_ERROR=f"RECORDING_DUMP var Found and @{Config.USER_ID} is not a admin of the group./ Channel"
            return False
    if Config.CHAT:
        try:
            k=await USER.get_chat_member(Config.CHAT, Config.USER_ID)
            if not k.status in ["administrator", "creator"]:
                LOGGER.warning(f"{Config.USER_ID} không phải là quản trị viên trong {Config.CHAT}, bạn nên chạy người dùng với tư cách là quản trị viên.")
            elif k.status in ["administrator", "creator"] and not k.can_manage_voice_chats:
                LOGGER.warning(f"{Config.USER_ID} không có quyền quản lý trò chuyện thoại, nên quảng cáo bằng quyền này.")
        except (ValueError, PeerIdInvalid, ChannelInvalid):
            Config.STARTUP_ERROR=f"Không tìm thấy tài khoản người dùng mà bạn đã tạo SESSION_STRING trên CHAT ({Config.CHAT})"
            LOGGER.error(f"Không tìm thấy tài khoản người dùng mà bạn đã tạo SESSION_STRING trên CHAT ({Config.CHAT})")
            return False
        try:
            k=await bot.get_chat_member(Config.CHAT, Config.BOT_USERNAME)
            if not k.status == "administrator":
                LOGGER.warning(f"{Config.BOT_USERNAME}, không phải là quản trị viên trong {Config.CHAT}, bạn nên chạy bot với tư cách là quản trị viên.")
        except (ValueError, PeerIdInvalid, ChannelInvalid):
            Config.STARTUP_ERROR=f"Không tìm thấy Bot trên CHAT, nên thêm {Config.BOT_USERNAME} to {Config.CHAT}"
            LOGGER.warning(f"Không tìm thấy Bot trên CHAT, nên thêm {Config.BOT_USERNAME} to {Config.CHAT}")
            pass
    if not Config.DATABASE_URI:
        LOGGER.warning("Không tìm thấy DATABASE_URI. Nên sử dụng cơ sở dữ liệu.")
    return True
