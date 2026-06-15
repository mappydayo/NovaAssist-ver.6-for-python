import asyncio
import os
import datetime
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# .envファイルから環境変数を読み込みます
load_dotenv()

# Discord Botのインテントを設定します
intents = discord.Intents.default()
# メッセージの内容を読み取るインテントを有効にします
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.active_timers = []

    async def setup_hook(self):
        # 起動時にスラッシュコマンドをDiscordに同期します
        guild_id = os.getenv("GUILD_ID")
        if guild_id:
            # GUILD_IDが設定されている場合は、そのサーバー向けに即時同期します
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"ギルド {guild_id} にコマンドを同期しました。")
        else:
            # 設定されていない場合はグローバル同期します（反映まで時間がかかる場合があります）
            await self.tree.sync()
            print("グローバルにコマンドを同期しました。")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"ログインしました: {bot.user}")

@bot.event
async def on_message(message):
    # 送信者がBot自身の場合は処理をスキップします
    if message.author == bot.user:
        return

    await bot.process_commands(message)

# スラッシュコマンド /ping の実装
@bot.tree.command(name="ping", description="pongと返します。")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong")

# スラッシュコマンド /timer の実装
@bot.tree.command(name="timer", description="指定した時間後にタイトルとメンションで通知します。")
@app_commands.describe(
    minutes="タイマーの時間（分単位、小数指定も可能。例: 0.5 で30秒）",
    title="タイマーのタイトル"
)
async def timer(interaction: discord.Interaction, minutes: float, title: str):
    if minutes <= 0:
        await interaction.response.send_message("時間は0より大きい値を指定してください。", ephemeral=True)
        return

    # 即座にタイマーを受け付けた旨を応答します
    await interaction.response.send_message(f"タイマーを設定しました: {title} ({minutes}分後)", ephemeral=True)

    # タイマー情報を登録
    end_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=minutes)
    timer_info = {
        "user_id": interaction.user.id,
        "user_name": interaction.user.name,
        "title": title,
        "end_time": end_time,
        "channel_id": interaction.channel_id
    }
    bot.active_timers.append(timer_info)

    try:
        # 待機処理（分から秒へ変換）
        seconds = minutes * 60
        await asyncio.sleep(seconds)

        # 指定時間経過後にメンション付きでメッセージを送信します
        user_mention = interaction.user.mention
        if interaction.channel:
            await interaction.channel.send(f"{user_mention} 時間になりました！\nタイトル: {title}")
        else:
            # チャンネル情報が取得できない場合のフォールバック処理
            await interaction.followup.send(f"{user_mention} 時間になりました！\nタイトル: {title}")
    finally:
        # 終了時にリストから削除
        if timer_info in bot.active_timers:
            bot.active_timers.remove(timer_info)

# スラッシュコマンド /timer_status の実装
@bot.tree.command(name="timer_status", description="実行中のタイマーの残り時間を確認します。")
async def timer_status(interaction: discord.Interaction):
    if not bot.active_timers:
        await interaction.response.send_message("現在実行中のタイマーはありません。", ephemeral=True)
        return

    now = datetime.datetime.now(datetime.timezone.utc)
    lines = ["現在実行中のタイマー一覧:"]
    for i, t in enumerate(bot.active_timers, 1):
        remaining = t["end_time"] - now
        remaining_seconds = remaining.total_seconds()
        if remaining_seconds < 0:
            remaining_seconds = 0
        remaining_minutes = remaining_seconds / 60
        
        lines.append(f"{i}. タイトル: {t['title']} | 設定者: {t['user_name']} | 残り時間: {remaining_minutes:.2f}分")

    await interaction.response.send_message("\n".join(lines), ephemeral=True)

def main():
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token or token == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("エラー: .envファイルにDiscord Botのトークンを設定してください。")
        return

    bot.run(token)

if __name__ == "__main__":
    main()
