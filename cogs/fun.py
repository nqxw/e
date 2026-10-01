# cogs/fun.py
import random, asyncio, aiohttp, discord
from discord.ext import commands
from . import state as S
import aiohttp
import asyncio

NEKO_ACTIONS = {"neko","hug","kiss","pat","slap","cuddle","poke","boop",
                "wave","bite","highfive","nom","tickle","yeet","blush","cry"}

class FunCog(commands.Cog, name="fun"):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="gayrate", brief="Gay rate")
    async def gayrate(self, ctx, user: discord.User = None):
        u = user or ctx.author
        rate = random.randint(0, 100)
        await ctx.message.edit(content=f"{u} is **{rate}%** gay 🏳️‍🌈")

    @commands.command(name="meme", brief="Random meme")
    async def meme(self, ctx):
        async with aiohttp.ClientSession() as s:
            async with s.get("https://meme-api.com/gimme") as r:
                if r.status == 200:
                    d = await r.json()
                    await ctx.message.edit(content=d.get("url","no meme found"))
                else:
                    await ctx.message.edit(content=S.ui_err("meme fetch failed"))

    @commands.command(name="joke", brief="Random joke")
    async def joke(self, ctx):
        async with aiohttp.ClientSession() as s:
            async with s.get("https://official-joke-api.appspot.com/random_joke") as r:
                if r.status == 200:
                    d = await r.json()
                    await ctx.message.edit(content=f"{d['setup']}\n||{d['punchline']}||")
                else:
                    await ctx.message.edit(content=S.ui_err("joke fetch failed"))

    async def _neko(self, ctx, action: str):
        url = f"https://nekos.best/api/v2/{action}"
        async with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                if r.status == 200:
                    d = await r.json()
                    results = d.get("results", [])
                    if results:
                        img = results[0].get("url","")
                        await ctx.message.edit(content=img); return
        await ctx.message.edit(content=S.ui_err("neko API failed"))

    @commands.command(name="neko")
    async def neko(self, ctx): await self._neko(ctx, "neko")
    @commands.command(name="hug")
    async def hug(self, ctx): await self._neko(ctx, "hug")
    @commands.command(name="kiss")
    async def kiss(self, ctx): await self._neko(ctx, "kiss")
    @commands.command(name="pat")
    async def pat(self, ctx): await self._neko(ctx, "pat")
    @commands.command(name="slap")
    async def slap(self, ctx): await self._neko(ctx, "slap")
    @commands.command(name="cuddle")
    async def cuddle(self, ctx): await self._neko(ctx, "cuddle")
    @commands.command(name="poke")
    async def poke(self, ctx): await self._neko(ctx, "poke")
    @commands.command(name="wave")
    async def wave(self, ctx): await self._neko(ctx, "wave")
    @commands.command(name="bite")
    async def bite(self, ctx): await self._neko(ctx, "bite")
    @commands.command(name="boop")
    async def boop(self, ctx): await self._neko(ctx, "boop")
    @commands.command(name="cry")
    async def cry(self, ctx): await self._neko(ctx, "cry")

async def setup(bot): await bot.add_cog(FunCog(bot))
