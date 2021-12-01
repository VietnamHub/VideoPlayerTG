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
from utils import LOGGER
try:
   import os
   import heroku3
   from dotenv import load_dotenv
   from ast import literal_eval as is_enabled

except ModuleNotFoundError:
    import os
    import sys
    import subprocess
    file=os.path.abspath("requirements.txt")
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', file, '--upgrade'])
    os.execl(sys.executable, sys.executable, *sys.argv)


class Config:
    #Telegram API Stuffs
    load_dotenv()  # load enviroment variables from .env file
    ADMIN = os.environ.get("ADMINS", '2106908020')
    SUDO = [int(admin) for admin in (ADMIN).split()] # Exclusive for heroku vars configuration.
    ADMINS = [int(admin) for admin in (ADMIN).split()] #group admins will be appended to this list.
    API_ID = int(os.environ.get("API_ID", ''))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")     
    SESSION = os.environ.get("SESSION_STRING", "")

    #Stream Chat and Log Group
    CHAT = int(os.environ.get("CHAT", ""))
    LOG_GROUP=os.environ.get("LOG_GROUP", "")

    #Stream 
    STREAM_URL=os.environ.get("STARTUP_STREAM", "https://www.youtube.com/watch?v=5qap5aO4i9A")
   
    #Database
    DATABASE_URI=os.environ.get("DATABASE_URI", None)
    DATABASE_NAME=os.environ.get("DATABASE_NAME", "VCPlayerBot")


    #heroku
    API_KEY=os.environ.get("HEROKU_API_KEY", None)
    APP_NAME=os.environ.get("HEROKU_APP_NAME", None)


    #Optional Configuration
    SHUFFLE=is_enabled(os.environ.get("SHUFFLE", 'True'))
    ADMIN_ONLY=is_enabled(os.environ.get("ADMIN_ONLY", "False"))
    REPLY_MESSAGE=os.environ.get("REPLY_MESSAGE", "Tham gia nhóm chat https://t.me/VietnamHub")
    EDIT_TITLE = os.environ.get("EDIT_TITLE", False)
    #others
    
    RECORDING_DUMP=os.environ.get("RECORDING_DUMP", False)
    RECORDING_TITLE=os.environ.get("RECORDING_TITLE", False)
    TIME_ZONE = os.environ.get("TIME_ZONE", "Asia/Ho_Chi_Minh")    
    IS_VIDEO=is_enabled(os.environ.get("IS_VIDEO", 'True'))
    IS_LOOP=is_enabled(os.environ.get("IS_LOOP", 'True'))
    DELAY=int(os.environ.get("DELAY", '10'))
    PORTRAIT=is_enabled(os.environ.get("PORTRAIT", 'False'))
    IS_VIDEO_RECORD=is_enabled(os.environ.get("IS_VIDEO_RECORD", 'True'))
    DEBUG=is_enabled(os.environ.get("DEBUG", 'False'))
    PTN=is_enabled(os.environ.get("PTN", "False"))

    #Quality vars
    E_BITRATE=os.environ.get("BITRATE", False)
    E_FPS=os.environ.get("FPS", False)
    CUSTOM_QUALITY=os.environ.get("QUALITY", "100")

    #Search filters for cplay
    FILTERS =  [filter.lower() for filter in (os.environ.get("FILTERS", "video document")).split(" ")]


    #Dont touch these, these are not for configuring player
    GET_FILE={}
    DATA={}
    STREAM_END={}
    SCHEDULED_STREAM={}
    DUR={}
    msg = {}

    SCHEDULE_LIST=[]
    playlist=[]
    CONFIG_LIST = ["ADMINS", "IS_VIDEO", "IS_LOOP", "REPLY_PM", "ADMIN_ONLY", "SHUFFLE", "EDIT_TITLE", "CHAT", 
    "SUDO", "REPLY_MESSAGE", "STREAM_URL", "DELAY", "LOG_GROUP", "SCHEDULED_STREAM", "SCHEDULE_LIST", 
    "IS_VIDEO_RECORD", "IS_RECORDING", "WAS_RECORDING", "RECORDING_TITLE", "PORTRAIT", "RECORDING_DUMP", "HAS_SCHEDULE", 
    "CUSTOM_QUALITY"]

    STARTUP_ERROR=None

    ADMIN_CACHE=False
    CALL_STATUS=False
    YPLAY=False
    YSTREAM=False
    CPLAY=False
    STREAM_SETUP=False
    LISTEN=False
    STREAM_LINK=False
    IS_RECORDING=False
    WAS_RECORDING=False
    PAUSE=False
    MUTED=False
    HAS_SCHEDULE=None
    IS_ACTIVE=None
    VOLUME=100
    CURRENT_CALL=None
    BOT_USERNAME=None
    USER_ID=None

    if LOG_GROUP:
        LOG_GROUP=int(LOG_GROUP)
    else:
        LOG_GROUP=None
    if not API_KEY or \
       not APP_NAME:
       HEROKU_APP=None
    else:
       HEROKU_APP=heroku3.from_key(API_KEY).apps()[APP_NAME]


    if EDIT_TITLE in ["NO", 'False']:
        EDIT_TITLE=False
        LOGGER.info("Đã tắt Chỉnh sửa Tiêu đề")
    if REPLY_MESSAGE:
        REPLY_MESSAGE=REPLY_MESSAGE
        REPLY_PM=True
        LOGGER.info("Đã tìm thấy tin nhắn trả lời, đã bật PM MSG")
    else:
        REPLY_MESSAGE=False
        REPLY_PM=False

    if E_BITRATE:
       try:
          BITRATE=int(E_BITRATE)
       except:
          LOGGER.error("Tốc độ bit được chỉ định không hợp lệ.")
          E_BITRATE=False
          BITRATE=48000
       if not BITRATE >= 48000:
          BITRATE=48000
    else:
       BITRATE=48000
    
    if E_FPS:
       try:
          FPS=int(E_FPS)
       except:
          LOGGER.error("FPS được chỉ định không hợp lệ")
          E_FPS=False
       if not FPS >= 30:
          FPS=30
    else:
       FPS=30
    try:
       CUSTOM_QUALITY=int(CUSTOM_QUALITY)
       if CUSTOM_QUALITY > 100:
          CUSTOM_QUALITY = 100
          LOGGER.warning("chất lượng tối đa cho phép là 100, chất lượng đã chỉ định không hợp lệ. Chất lượng được đặt thành 100")
       elif CUSTOM_QUALITY < 10:
          LOGGER.warning("Chất lượng tối thiểu được phép là 10, Qulaity được đặt thành 10")
          CUSTOM_QUALITY = 10
       if  66.9  < CUSTOM_QUALITY < 100:
          if not E_BITRATE:
             BITRATE=48000
       elif 50 < CUSTOM_QUALITY < 66.9:
          if not E_BITRATE:
             BITRATE=36000
       else:
          if not E_BITRATE:
             BITRATE=24000
    except:
       if CUSTOM_QUALITY.lower() == 'high':
          CUSTOM_QUALITY=100
       elif CUSTOM_QUALITY.lower() == 'medium':
          CUSTOM_QUALITY=66.9
       elif CUSTOM_QUALITY.lower() == 'low':
          CUSTOM_QUALITY=50
       else:
          LOGGER.warning("Đã chỉ định CHẤT LƯỢNG không hợp lệ. Dẫn đến Cao.")
          CUSTOM_QUALITY=100



    #help strings 
    PLAY_HELP="""
__Bạn có thể chơi bằng bất kỳ tùy chọn nào trong số này__

1. Phát video từ liên kết YouTube.
Command: **/live**
__Bạn có thể sử dụng điều này như một câu trả lời cho một liên kết YouTube hoặc chuyển liên kết theo lệnh. hoặc dưới dạng trả lời tin nhắn để tìm kiếm tin nhắn đó trong YouTube.__

2. Phát từ một tệp điện tín.
Command: **/live**
__Trả lời phương tiện được hỗ trợ (video và tài liệu hoặc tệp âm thanh).__
Lưu ý: __Đối với cả hai trường hợp /fplay cũng có thể được quản trị viên sử dụng để phát bài hát ngay lập tức mà không cần đợi kết thúc hàng đợi.__

3. Play from a YouTube playlist
Command: **/yplay**
__Đầu tiên, lấy một tệp danh sách phát từ @vietnamhub và trả lời tệp danh sách phát.__

4. Live Stream
Command: **/stream**
__Chuyển URL luồng trực tiếp hoặc bất kỳ URL trực tiếp nào để phát dưới dạng luồng.__

5. Import an old playlist.
Command: **/import**
__Trả lời tệp danh sách phát đã xuất trước đó.__

6. Channel Play
Command: **/cplay**
__Use `/cplay tên người dùng kênh hoặc id kênh` để phát tất cả các tệp từ kênh nhất định.
Theo mặc định, cả tệp video và tài liệu sẽ được phát. Bạn có thể thêm hoặc xóa loại tệp bằng cách sử dụng `FILTERS` var. 
Ví dụ: để phát trực tuyến âm thanh, video và tài liệu từ kênh sử dụng `/env FILTERS video document audio` . Nếu bạn chỉ cần âm thanh, bạn có thể sử dụng`/env FILTERS video audio` và như thế.
Để thiết lập các tệp từ một kênh dưới dạng STARTUP_STREAM, để các tệp sẽ được tự động thêm vào danh sách phát khi khởi động bot. sử dụng `/env STARTUP_STREAM tên người dùng kênh hoặc id kênh`

Lưu ý rằng đối với các kênh công khai, bạn nên sử dụng tên người dùng của các kênh cùng với '@' và đối với các kênh riêng tư, bạn nên sử dụng id kênh.
Đối với các kênh riêng tư, hãy đảm bảo cả tài khoản bot và USER đều là thành viên của kênh.__
"""
    SETTINGS_HELP="""
**Bạn có thể dễ dàng tùy chỉnh trình phát của mình theo nhu cầu của bạn. Các cấu hình sau có sẵn:**

🔹Command: **/settings**

🔹CÁC CẤU HÌNH CÓ SN:

**Player Mode** -  __Điều này cho phép bạn chạy trình phát của mình dưới dạng trình phát nhạc 24/7 hoặc chỉ khi có bài hát trong hàng đợi. 
Nếu bị tắt, trình phát sẽ rời khỏi cuộc gọi khi danh sách phát trống.
Nếu không thì STARTUP_STREAM sẽ được phát trực tuyến khi id danh sách phát trống.__

**Video Enabled** -  __Điều này cho phép bạn chuyển đổi giữa âm thanh và video.
nếu bị vô hiệu hóa, các tệp video sẽ được phát dưới dạng âm thanh.__

**Admin Only** - __Bật điều này sẽ hạn chế người dùng không phải quản trị viên sử dụng lệnh chơi.__

**Edit Title** - __Bật tính năng này sẽ chỉnh sửa tiêu đề VideoChat của bạn thành tên bài hát đang phát hiện tại.__

**Shuffle Mode** - __Bật tính năng này sẽ phát ngẫu nhiên danh sách phát bất cứ khi nào bạn nhập danh sách phát hoặc sử dụng /yplay __

**Auto Reply** - __Chọn có trả lời tin nhắn PM của tài khoản người dùng đang chơi hay không.
Bạn có thể thiết lập một tin nhắn trả lời tùy chỉnh bằng cách sử dụng confug `REPLY_MESSAGE`.__

"""
    SCHEDULER_HELP="""
__VCPlayer cho phép bạn lên lịch một luồng.
Điều này có nghĩa là bạn có thể lên lịch phát trực tiếp vào một ngày trong tương lai và vào ngày đã lên lịch, luồng sẽ được phát tự động.
Hiện tại, bạn có thể lên lịch phát trực tiếp trong một năm !!. Đảm bảo rằng bạn đã thiết lập một cơ sở dữ liệu, nếu không, bạn sẽ mất lịch trình của mình bất cứ khi nào trình phát khởi động lại. __

Command: **/schedule**

__Trả lời một tệp hoặc một video youtube hoặc thậm chí một tin nhắn văn bản với lệnh lịch trình.
Phương tiện truyền thông hoặc video youtube đã trả lời sẽ được lên lịch và sẽ phát vào ngày đã định.
Thời gian lập lịch theo mặc định trong IST và bạn có thể thay đổi múi giờ bằng cách sử dụng cấu hình `TIME_ZONE`.__

Command: **/slist**
__Xem các luồng đã lên lịch hiện tại của bạn.__

Command: **/cancel**
__Hủy lịch trình bằng id lịch biểu của nó, Bạn có thể lấy id lịch trình bằng lệnh /slist__

Command: **/cancelall**
__Hủy tất cả các luồng đã lên lịch__
"""
    RECORDER_HELP="""
__Với VCPlayer, bạn có thể dễ dàng ghi lại tất cả các cuộc trò chuyện video của mình.
Theo mặc định, điện tín cho phép bạn ghi trong thời gian tối đa là 4 giờ.
Một nỗ lực để vượt qua giới hạn này đã được thực hiện bằng cách tự động khởi động lại quá trình ghi sau 4 giờ__

Command: **/record**

CÁC CẤU HÌNH CÓ SN:
1. Record Video: __Nếu được bật, cả video và âm thanh của luồng sẽ được ghi lại, nếu không, chỉ âm thanh sẽ được ghi.__

2. Video dimension: __Chọn giữa kích thước dọc và ngang để ghi âm của bạn__

3. Custom Recording Title: __Thiết lập tiêu đề bản ghi tùy chỉnh cho bản ghi của bạn. Sử dụng một lệnh /rtitle để cấu hình cái này.
Để tắt tiêu đề tùy chỉnh, hãy sử dụng `/rtitle False `__

4. Recording Dumb: __Bạn có thể thiết lập chuyển tiếp tất cả các bản ghi của mình tới một kênh, điều này sẽ hữu ích vì nếu không, các bản ghi sẽ được gửi đến tin nhắn đã lưu của tài khoản phát trực tuyến.
Thiết lập bằng cách sử dụng cấu hình`RECORDING_DUMP` .__

⚠️ Nếu bạn bắt đầu ghi bằng vcplayer, hãy đảm bảo rằng bạn cũng dừng lại với vcplayer.

"""

    CONTROL_HELP="""
__VCPlayer cho phép bạn kiểm soát các luồng của mình một cách dễ dàng__
1. Bỏ qua một bài hát.
Command: **/skip**
__Bạn có thể vượt qua một số lớn hơn 2 để bỏ qua bài hát ở vị trí đó.__

2. Tạm dừng trình phát.
Command: **/pause**

3. Tiếp tục trình phát.
Command: **/resume**

4. Thây đổi độ lơn âm thanh.
Command: **/volume**
__Pass the volume in between 1-200.__

5. Bỏ VC.
Command: **/leave**

6. Phát ngẫu nhiên danh sách phát.
Command: **/shuffle**

7. Xóa hàng đợi danh sách phát hiện tại.
Command: **/clearplaylist**

8. Tìm kiếm video.
Command: **/seek**
__Bạn có thể vượt qua số giây được bỏ qua. Ví dụ: /seek 10 để bỏ qua 10 giây. /seek -10 để tua lại 10 giây.__

9. Tắt tiếng trình phát.
Command: **/vcmute**

10. Bật tiếng trình phát.
Command : **/vcunmute**

11. Hiển thị danh sách phát.
Command: **/playlist** 
__Sử dụng /player hiển thị bằng các nút điều khiển__
"""

    ADMIN_HELP="""
__VCPlayer cho phép kiểm soát quản trị viên, tức là bạn có thể thêm quản trị viên và loại bỏ họ một cách dễ dàng.
Bạn nên sử dụng cơ sở dữ liệu MongoDb để có trải nghiệm tốt hơn, nếu không, tất cả những gì bạn quản trị viên sẽ được đặt lại sau khi khởi động lại.__

Command: **/vcpromote**
__Bạn có thể thăng cấp quản trị viên bằng tên người dùng hoặc id người dùng của họ hoặc bằng cách trả lời tin nhắn của người dùng đó.__

Command: **/vcdemote**
__Xóa quản trị viên khỏi danh sách quản trị viên__

Command: **/refresh**
__Làm mới danh sách quản trị viên trò chuyện__
"""

    MISC_HELP="""
Command: **/export**
__VCPlayer cho phép bạn xuất danh sách phát hiện tại của mình để sử dụng trong tương lai.__
__Một tệp json sẽ được gửi cho bạn và tệp này có thể được sử dụng cùng /import command.__

Command : **/logs**
__Nếu trình phát của bạn gặp sự cố, bạn có thể dễ dàng kiểm tra nhật ký bằng cách sử dụng /logs__
 
Command : **/env**
__Thiết lập vars cấu hình của bạn bằng lệnh /env.__
__Example: To set up a__ `REPLY_MESSAGE` __use__ `/env REPLY_MESSAGE=Hey, Kiểm tra @ yeu69 thay vì gửi thư rác trong PM của tôi`__
__You can delete a config var by ommiting a value for that, Example:__ `/env LOG_GROUP=` __điều này sẽ xóa hiện tại LOG_GROUP config.

Command: **/config**
__Giống như cách sử dụng /env**

Command: **/update**
__Cập nhật bot của bạn với những thay đổi mới nhất__

Tip: __Bạn có thể dễ dàng thay đổi cấu hình CHAT bằng cách thêm tài khoản người dùng và tài khoản bot vào bất kỳ nhóm nào khác và bất kỳ lệnh nào trong nhóm mới__

"""
    ENV_HELP="""
**Đây là những vars có thể định cấu hình có sẵn và bạn có thể đặt từng vars bằng cách sử dụng kênh /env**


**Vars bắt buộc**

1. `API_ID` : __Get From [my.telegram.org](https://my.telegram.org/)__

2. `API_HASH` : __Get from [my.telegram.org](https://my.telegram.org)__

3. `BOT_TOKEN` : __[@Botfather](https://telegram.dog/BotFather)__

4. `SESSION_STRING` : __Tạo từ đây [GenerateStringName](https://t.me/phiendangnhap_bot)__

5. `CHAT` : __ID của Kênh / Nhóm nơi bot phát Nhạc.__

6. `STARTUP_STREAM` : __Điều này sẽ được phát trực tiếp khi khởi động và khởi động lại bot. 
Bạn có thể sử dụng bất kỳ STREAM_URL nào hoặc liên kết trực tiếp của bất kỳ video nào hoặc liên kết Trực tiếp trên Youtube.
Bạn cũng có thể sử dụng Danh sách phát trên YouTube. Tìm Liên kết Telegram cho danh sách phát của bạn từ [PlayList Dumb](https://t.me/vietnamhub) hoặc nhận PlayList từ [PlayList Extract](https://t.me/yeu69). 
Liên kết PlayList phải ở dạng `https://t.me/owogram/xxx`
Bạn cũng có thể sử dụng các tệp từ một kênh làm luồng khởi động. Đối với điều đó, chỉ cần sử dụng id kênh hoặc tên người dùng kênh của kênh làm giá trị STARTUP_STREAM.
Để biết thêm thông tin về phát kênh, hãy đọc trợ giúp từ phần trình phát.__

**Vars tùy chọn được đề xuất**

1. `DATABASE_URI`: __Url cơ sở dữ liệu MongoDB, lấy từ [mongodb](https://cloud.mongodb.com). This is an optional var, but it is recomonded to use this to experiance the full features.__

2. `HEROKU_API_KEY`: __Phím api heroku của bạn. Nhận một từ [tại đây](https://dashboard.heroku.com/account/applications/authorizations/new)__

3. `HEROKU_APP_NAME`: __Tên ứng dụng heroku của bạn.__

4. `FILTERS`: __Bộ lọc để tìm kiếm tệp phát kênh. Đọc trợ giúp về cplay trong phần trình phát.__

**Các Vars tùy chọn khác**
1. `LOG_GROUP` : __Nhóm để gửi Danh sách phát, nếu CHAT là một Nhóm__

2. `ADMINS` : __ID của người dùng có thể sử dụng lệnh quản trị.__

3. `REPLY_MESSAGE` : __Một câu trả lời cho những người nhắn tin cho tài khoản USER trong PM. Để trống nếu bạn không cần tính năng này. (Có thể cấu hình thông qua các nút nếu mongodb được thêm vào. Sử dụng /caidat)__

4. `ADMIN_ONLY` : __Vượt qua `True` nếu bạn muốn thực hiện /live lệnh chỉ dành cho quản trị viên của `CHAT`. Theo mặc định /live có sẵn cho tất cả. (Có thể cấu hình thông qua các nút nếu mongodb được thêm vào. Sử dụng /caidat)__

5. `DATABASE_NAME`: __Tên cơ sở dữ liệu cho cơ sở dữ liệu mongodb của bạn.mongodb__

6. `SHUFFLE` : __Làm cho nó `False` nếu bạn không muốn xáo trộn danh sách phát. (Có thể cấu hình thông qua các nút)__

7. `EDIT_TITLE` : __Đặt nó thành `False` nếu bạn không muốn bot chỉnh sửa tiêu đề trò chuyện video theo bài hát đang phát.(Có thể cấu hình thông qua các nút nếu mongodb được thêm vào. Sử dụng /settings)__

8. `RECORDING_DUMP` : __ID kênh với tài khoản USER làm quản trị viên, để kết xuất các bản ghi trò chuyện video.__

9. `RECORDING_TITLE`: __Tiêu đề tùy chỉnh cho bản ghi video trò chuyện của bạn.__

10. `TIME_ZONE` : __Múi giờ của quốc gia bạn, theo mặc định là IST__

11. `IS_VIDEO_RECORD` : __Đặt nó thành `False` nếu bạn không muốn quay video và chỉ âm thanh sẽ được ghi. (Có thể định cấu hình thông qua các nút nếu mongodb được thêm vào. Sử dụng / ghi lại)__

12. `IS_LOOP` ; __Make it `False` if you do not want 24 / 7 Video Chat. (Configurable through buttons if mongodb added.Use /caidat)__

13. `IS_VIDEO` : __Hãy biến nó thành `False` nếu bạn muốn sử dụng trình phát làm trình phát nhạc mà không có video. (Có thể cấu hình thông qua các nút nếu mongodb được thêm vào. Sử dụng/caidat)__

14. `PORTRAIT`: __Đặt nó thành True nếu bạn muốn quay video ở chế độ dọc. (Có thể cấu hình thông qua các nút nếu mongodb được thêm vào. Sử dụng /record)__

15. `DELAY` : __Chọn giới hạn thời gian cho việc xóa lệnh. 10 giây theo mặc định.__

16. `QUALITY` : __Tùy chỉnh chất lượng của trò chuyện video, sử dụng một trong các `high`, `medium`, `low` . __

17. `BITRATE` : __Tốc độ bit của âm thanh (Không nên thay đổi).__

18. `FPS` : __Fps của video sẽ phát (Không nên thay đổi.)__

"""
