# 跨管线坑单总表

各管线专属坑同时写在 `registry/pipelines/<id>.yaml` 的 `pitfalls`；本表是汇总视图。
P1 起各条迁入 `skills/<id>/references/pitfalls.md`。新增坑时两处同步。

来源 `workspace auto-memory` = 主会话跨项目记忆（`~/.claude/projects/.../memory/`，括号内为条目名）。
"未量化"表示只有定性结论。

| 管线 | 现象 | 根因 / 规避 | 量化证据 | 来源 |
|---|---|---|---|---|
| imgen | `background=transparent` 请求失败 | 不支持透明底参数；改纯白底渲染 + 后期抠白 | 502 | auto-memory（reference_imgen_no_transparent_bg） |
| imgen | 要 9:16 却去 outpaint | `size=auto` + prompt 写明 9:16 即出真 9:16 | — | auto-memory（reference_imgen_9_16_via_auto） |
| imgen | 英气女角出成男性 | 不写性别默认成男，androgynous 主导；先写 unmistakably a WOMAN + her + 女性体征再加英气，每镜重写 | 未量化 | auto-memory（reference_imgen_gender_lock_before_modifier） |
| imgen | 批量出图慢 / n>1 报错 | n>1 中转层坏；并发 per-key × per-model 可叠加，走 `imgen_batch.py` 多 key | 5 key × 3 模型约 14x | auto-memory（reference_imgen_parallel_capacity） |
| imgen | 精确比例守不住 | AI 出图做不到；精确比例只能合成 / 引擎 | 1:1 / 2:3 写死也守不住 | auto-memory（feedback_ai_image_no_exact_ratio） |
| imgen | 画面"脏" | 明度脏：删 muted/vignette，加 luminous/limited-palette；密度脏：铺满零留白，正向留白词压不过反向堆料词，要删堆料词 | 未量化 | auto-memory（feedback_image_luminous_not_muddy / feedback_image_dirty_is_density_not_only_luminance） |
| cutout | 入引擎有白边光晕 | 抠后必须 defringe，腐蚀 alpha 边缘约 2px | ~2px | auto-memory（feedback_cut_pipeline_defringe） |
| cutout | 内部困白 / alpha 碎岛漏检 | 白底看不出；必须在洋红底上验，`check_cutout.py` 当闸 | 未量化 | auto-memory（feedback_cutout_verify_on_chroma） |
| cutout | 白主色图抠坏 | 用绿幕 chroma 而非白底；四套方法：硬边腐蚀 / 发光反预乘 / 含内部白 flood-fill / 绿幕 | 未量化 | auto-memory（reference_white_screen_unpremultiply_keying） |
| cutout | 棋盘 tile 接缝黑锯齿 | 不从场景图抠；几何程序化 + 材质 AI + 程序化辉光边 | 未量化 | auto-memory（feedback_tile_not_cut_from_scene） |
| sprite | 帧间抖动 | 靠后处理钉脚底不靠 prompt；锁 feetY 锚点而非尺寸 | 271px → 1px | auto-memory（feedback_sprite_jitter_postprocess_not_prompt） |
| sprite | 呼吸动画角色整体缩放 | 不用整体 scale；上半身微动 + 下半身锁定 | 未量化 | auto-memory（feedback_breathing_no_scale） |
| sprite | 系列图尺寸 / 构图 / 风格漂 | 先定一个 anchor 再 ref 它生成其余 | 未量化 | auto-memory（feedback_series_anchor_standard） |
| sprite | 同稀有度跨类型边框不一致 | 边框 / 件坐标须一致；同 master ref 生成后 harness 比对 | 未量化 | auto-memory（feedback_cross_type_frame_consistency） |
| shots | 4K 下 UI 错位未被发现 | 默认 1080p + 制作人 4K（3840×1907）两套；DOM UI 随视口缩放，不用裸 px | 3840×1907 | auto-memory（feedback_screenshot_at_producer_resolution） |
| shots | 调了半天发现渲染的不是目标素材 | 先确认渲染的是目标本身，非背景 / 它件冒充；三处都对却异常用 tint / 纯色探针 | 未量化 | auto-memory（feedback_verify_rendered_asset_not_proxy） |
| shots | WebGL 纹理空白 | `file://` 的 `<img>` 当纹理跨源报错；改 data-URI 或起服务器 | 未量化 | auto-memory（reference_webgl_fileurl_datauri） |
| shots | 截到别的项目 | pawkov 8378/8380/8381/8388 与 blender-lab 8381 撞；启动前扫端口 | 未量化 | auto-memory（reference_pawkov_ports_8381_collision） |
| shots | 画布全黑 | MCP 浏览器窗口 hidden（dragon-cliff-three） | 未量化 | auto-memory（project_dragon_cliff_three） |
| shots | FPS / 时序数据不可信 | headless shell 走 SwiftShader，FPS 作废；并行 WebGL 上下文游戏时间漂移 | 作者自述 | docs/projects/threejs-game-skills |
| char3d / blender | 衣冠件错位 / 糊 | mesh 槽不吃 dx/dy 要 align_to_stencil；mipmap 开关在 .atlas filter 行；装饰线源图 ≥6–8px；面罩跨物种用 faceAnchor:nose（pawkov） | ≥6–8px | auto-memory（reference_pawkov_costume_mesh_pipeline） |
| char3d / blender | 自绘物种件有深灰外圈 | 不加 rim 描边；内部结构线照留 | 未量化 | auto-memory（feedback_self_drawn_species_no_rim） |
| char3d | Tripo 绑骨 / 动画失败 | v2.x rigger 人形失败；`--animate-in-place` 毁烘焙；v1.0 retarget 必 FBX | 人形 0/16（作者自述） | docs/projects/threejs-game-skills |
| char3d / blender | LoRA 训练出缺陷 | 训练集绝不用有缺陷 / 没达预期的图 | 未量化 | auto-memory（feedback_lora_trainset_quality） |
| comfy / img2three | Qwen-Image-2.1 用法与许可 | 原生 RGBA 免抠图；int8 比 bf16 慢；同 seed 吃缓存测速要换 seed；**非商用** | 未量化 | auto-memory（reference_qwen_image_2_1_local） |
| comfy / img2three | 工具选错 | imgen MCP 做风格探索 / 单张；可复现 / 受控 / 序列帧才用 ComfyUI | 未量化 | auto-memory（feedback_imgen_mcp_vs_comfyui） |
| comfy / img2three | 误动别的实例 | 8189 是别的 ComfyUI 实例别碰；comfy-lab 09-21 更到 v0.37 | 未量化 | auto-memory（project_comfy_lab） |
| audio | 克隆音色质量差 | 文件名 ≠ 逐字转写；prompt_text 必须听原文校验 | 未量化 | auto-memory（feedback_filename_not_transcription） |
| audio | TTS 引擎坑 | CosyVoice3 endofprompt / instruct 坑；Fish 单独批 | Fish 19G | auto-memory（reference_tts_engines_local） |
| audio | BGM 长度不稳 / 许可 | MiniMax Music 3 长度随 seed 摆动无平台；**非商用**；用户 2026-09-05 拍板暂不进生产线 | 未量化 | auto-memory（reference_minimax_music3_local） |
| mining | B 站下载 412 | curl_cffi 换 buvid + wbi 签名 playurl 取流；yt-dlp / 浏览器 cookies 都失败 | 412 | auto-memory（reference_bilibili_download_412_bypass） |
| mining | git add 失败 | Windows 保留名（aux / con / nul）作文件名；提交前 `git add -n` 干跑 | 未量化 | auto-memory（reference_windows_reserved_filenames） |
| 通用 | 大文件下载慢 / 卡死 | 默认 aria2c；直连源加 `--no-proxy="*"`；HF Xet CDN 须 `--all-proxy=http://127.0.0.1:7897` | 直连 HF Xet 0B 卡死 | auto-memory（feedback_default_download_aria2c） |
| 通用 | WebFetch 403 拿不到正文 | 兜底 `scripts/chrome_fetch.py`（真 Chrome 有头） | 未量化 | auto-memory（reference_chrome_fetch_fallback） |
| 通用 | implementer 写大文件中途断连 | 分块写，每次 ≤250 行 | ~1500 行一次写会断 | auto-memory（reference_subagent_large_write_chunking） |
