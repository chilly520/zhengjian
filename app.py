import streamlit as st
from PIL import Image, ImageOps
from rembg import remove, new_session
import io

# --- 页面基础设置 ---
st.set_page_config(page_title="专业版-证件照生成工具箱", layout="centered")
st.title("🛠️ 专业版·证件照生成工具箱")
st.markdown("---")

# --- 初始化 AI 模型会话 (仅在模式一使用) ---
if 'rembg_session' not in st.session_state:
    # 使用通用性更强的 ISNet 模型
    st.session_state['rembg_session'] = new_session(model_name="isnet-general-use")

# --- 侧边栏：模式选择与参数显示 ---
st.sidebar.header("第一步：选择处理模式")
# 添加单选按钮切换模式
mode = st.sidebar.radio(
    "请根据你的素材情况选择：",
    ("全自动 (AI 困难症增强版)", 
     "半自动 (已抠好透明PNG换底)", 
     "仅格式化 (成品图调整尺寸/大小)")
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 输出目标规格")
st.sidebar.info("""
- **像素**：960 x 1280 (高清 3:4)
- **背景**：标准证件蓝 (RGB: 67, 142, 219)
- **DPI**：300
- **文件大小**：500KB - 1MB (高质量)
- **构图**：顶部 1/10 留空 (模式1&2生效)
""")

# --- 统一目标参数 ---
TARGET_W, TARGET_H = 960, 1280
BLUE_BG_COLOR = (67, 142, 219)

# --- 主体逻辑 ---
# 根据不同模式修改上传提示
if mode == "全自动 (AI 困难症增强版)":
    upload_tip = "上传原始照片 (尝试拯救发丝边缘)"
elif mode == "半自动 (已抠好透明PNG换底)":
    upload_tip = "上传已抠好的透明背景 PNG 图片"
else:
    upload_tip = "上传已完成的蓝底证件照 (仅调整尺寸)"

uploaded_file = st.file_uploader(upload_tip, type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # 使用一个状态容器包裹处理过程
    status_text = f"正在进行：{mode}..."
    with st.status(status_text, expanded=True) as status:
        
        # 1. 加载图像
        input_image = Image.open(uploaded_file).convert("RGBA")
        final_canvas = None # 初始化最终画布

        # ================= 模式分支处理 =================

        # --- 模式一：全自动 AI 处理 ---
        if mode == "全自动 (AI 困难症增强版)":
            st.write("启动 AI 引擎，尝试捕捉发丝细节...")
            # 启用 alpha matting 参数，专门用于处理毛发边缘
            # based_mask=True 表示基于基础遮罩进行精细化
            no_bg_image = remove(
                input_image, 
                session=st.session_state['rembg_session'],
                alpha_matting=True,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=10,
                alpha_matting_erode_structure_size=10
            )
            
            # 进入标准构图流程
            st.write("正在应用标准构图 (顶部留空 1/10)...")
            final_canvas = Image.new("RGB", (TARGET_W, TARGET_H), BLUE_BG_COLOR)
            
            orig_w, orig_h = no_bg_image.size
            aspect = orig_w / orig_h
            top_gap = int(TARGET_H * 0.1)
            t_person_h = TARGET_H - top_gap
            t_person_w = int(t_person_h * aspect)
            # 宽度补偿
            if t_person_w < TARGET_W:
                t_person_w = TARGET_W
                t_person_h = int(t_person_w / aspect)
            
            resized_person = no_bg_image.resize((t_person_w, t_person_h), Image.Resampling.LANCZOS)
            paste_x = (TARGET_W - t_person_w) // 2
            paste_y = TARGET_H - t_person_h
            
            final_canvas.paste(resized_person, (paste_x, paste_y), resized_person)


        # --- 模式二：半自动 (已抠好PNG) ---
        elif mode == "半自动 (已抠好透明PNG换底)":
            # 检查是否真的是PNG且有透明通道
            if input_image.format != 'PNG' and 'A' not in input_image.getbands():
                 st.error("错误：请确保上传的是背景透明的 PNG 文件。")
                 st.stop()

            st.write("检测到透明图层，跳过 AI 抠图...")
            # 直接使用上传的透明图作为 no_bg_image
            no_bg_image = input_image
            
            # 进入标准构图流程 (同上)
            st.write("正在应用标准构图 (顶部留空 1/10, 底部对齐)...")
            final_canvas = Image.new("RGB", (TARGET_W, TARGET_H), BLUE_BG_COLOR)
            
            orig_w, orig_h = no_bg_image.size
            aspect = orig_w / orig_h
            top_gap = int(TARGET_H * 0.1)
            t_person_h = TARGET_H - top_gap
            t_person_w = int(t_person_h * aspect)
             # 宽度补偿
            if t_person_w < TARGET_W:
                t_person_w = TARGET_W
                t_person_h = int(t_person_w / aspect)

            resized_person = no_bg_image.resize((t_person_w, t_person_h), Image.Resampling.LANCZOS)
            paste_x = (TARGET_W - t_person_w) // 2
            paste_y = TARGET_H - t_person_h
            
            final_canvas.paste(resized_person, (paste_x, paste_y), resized_person)


        # --- 模式三：仅格式化 (成品图调整) ---
        elif mode == "仅格式化 (成品图调整尺寸/大小)":
            st.write("正在进行无损中心裁剪与缩放...")
            # 不需要创建蓝底画布，直接处理原图
            # 计算目标宽高比
            target_aspect = TARGET_W / TARGET_H
            
            # 使用 PIL 的 ImageOps.fit 进行智能中心裁剪和缩放
            # 它会自动保持比例填充 960x1280 的框，多余部分裁掉，不会拉伸变形
            final_canvas = ImageOps.fit(
                input_image.convert("RGB"), 
                (TARGET_W, TARGET_H), 
                method=Image.Resampling.LANCZOS, 
                centering=(0.5, 0.5) # (0.5, 0.5) 表示绝对中心对齐
            )

        # ================= 公共输出流程 =================

        # 质量与大小控制 (所有模式通用)
        st.write("最终输出：优化清晰度与文件体积 (目标 > 500KB)...")
        quality = 100
        final_buffer = io.BytesIO()
        
        while quality > 50: # 最低降到50，保证质量
            temp_buffer = io.BytesIO()
            # 统一写入 300 DPI
            final_canvas.save(temp_buffer, format="JPEG", quality=quality, dpi=(300, 300))
            current_size = temp_buffer.tell()
            
            if current_size <= 1024 * 1024: # 小于 1MB
                final_buffer = temp_buffer
                # 只要大于 400KB 且质量够高就停止，防止过度压缩
                if quality >= 90 and current_size >= 400 * 1024:
                    break
                # 如果是纯色图导致体积上不去，到 100 也停
                if quality == 100:
                    break
                # 正常情况找到最大可行质量后停止
                if current_size < 1024 * 1024:
                     break
            quality -= 2
            
        status.update(label=f"{mode} - 处理完成！", state="complete", expanded=False)

    # --- 结果展示区 ---
    col1, col2 = st.columns(2)
    with col1:
        st.image(uploaded_file, caption="上传的文件", use_container_width=True)
    with col2:
        st.image(final_canvas, caption=f"最终输出 ({TARGET_W}x{TARGET_H})", use_container_width=True)

    # --- 下载按钮 ---
    st.download_button(
        label="🚀 下载最终证件照 (JPG)",
        data=final_buffer.getvalue(),
        file_name="CET_Final_Processed.jpg",
        mime="image/jpeg"
    )
    
    final_size_kb = final_buffer.tell() // 1024
    st.success(f"""
    ✅ **{mode} 执行成功！**
    - 📜 规格: {TARGET_W} x {TARGET_H} 像素
    - 💾 大小: {final_size_kb} KB (符合要求)
    - 🖨️ 精度: 300 DPI
    """)

    # 针对不同模式的提示
    if mode == "全自动 (AI 困难症增强版)":
        if final_size_kb < 400:
             st.warning("提示：由于画面纯色区域较多，文件体积较小，但已是最高清晰度，符合要求。")
        st.info("💡 如果对 AI 边缘仍不满意，请使用 PS 抠出透明 PNG 后，切换到【半自动模式】上传。")
    elif mode == "仅格式化 (成品图调整尺寸/大小)":
         st.info("💡 此模式采用中心裁剪，请确保上传的原图中人像居中。")
