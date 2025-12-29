---
title: ""
description: "这里可以写你的网站描述"
date: 2025-12-29
layout: "home"
---

<div style="
    margin-top: 0rem;
    width: 100vw; 
    height: 100vh;
    margin-left: calc(50% - 50vw); 
    overflow: hidden; 
    position: relative; 
    margin-bottom: 2rem;">
    <video autoplay loop muted playsinline style="
        width: 100%; 
        height: 100%; 
        object-fit: cover;">
        <source src="/videos/hero.mp4" type="video/mp4">
        您的浏览器不支持视频播放。
    </video>
    
    <!-- 这里是视频上面的文字，如果不需要可以删掉下面这几行 -->
    <div style="
        position: absolute; 
        top: 50%; 
        left: 50%; 
        transform: translate(-50%, -50%); 
        color: white; 
        text-shadow: 0 0 10px black;
        text-align: center;">
        <h1>欢迎来到我的世界</h1>
        <p>Keep Simple, Keep Coding</p>
    </div>
    <!-- 文字部分结束 -->
</div>
