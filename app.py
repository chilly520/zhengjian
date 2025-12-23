import streamlit as st
from PIL import Image, ImageOps
from rembg import remove, new_session
import io
import gc  # 内存回收库，防止“超出资源限制”

# --- 1. 页面配置与内存清理 ---
st.set_page_config(page_title="高清证件照工具箱", layout="centered")

# 每次运行脚本前尝试清理一次内存
gc.collect()

st.title("📸 高清证件照专业工具箱")
st.markdown("---")

# --- 2. 初始化 AI 模型会话 ---
@st.cache_resource
def get_rembg_session():
    # 使用 isnet-general-use 模型，它在处理发丝边缘时相对更强
    return new_session(model_name="isnet-general-use")

# --- 3. 侧边栏设置 ---
st.sidebar.header("🚀 第一步：功能选择")
mode = st.sidebar.radio(
    "根据素材选择模式：",
    ("全自动 AI 模式 (发丝优化版)", 
     "半自动模式 (上传透明PNG换底)", 
     "仅格式化 (成品图调尺寸/体积)")
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 锁定规格 (已调优)")
st.sidebar.info("""
- **分辨率**: 960x1280 (3:4)
- **打印精度**: 300 DPI
- **目标体积**: 约 500KB
- **构图**: 顶部 1/10 留空
""")

# --- 4. 核心参数定义 ---
TARGET_W, TARGET_H = 960, 1280
BLUE_BG_COLOR = (67, 142, 219)

# --- 5. 文件上传 ---
if mode == "全自动 AI 模式 (发丝优化版)":
    tip = "上传原始照片 (背景越简单，AI 效果越好)"
elif mode == "半自动模式 (上传透明PNG换底)":
    tip = "上传你在 PS 中扣好的透明背景 PNG"
else:
    tip = "上传已有的蓝底照片 (仅修正尺寸/大小)"

uploaded_file = st.file_uploader(tip, type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    with st.status(f"正在以 {mode} 处理中...", expanded=True) as status:
        
        # 加载并统一转为 RGBA 模式
        input_image = Image.open(uploaded_file).convert("RGBA")
        final_canvas = None 

        # --- 分模式逻辑处理 ---
        if mode == "全自动 AI 模式 (发丝优化版)":
            st.write("AI 正在计算发丝边缘...")
            session = get_rembg_session()
            # 开启 alpha_matting 尝试保留更多发丝细节
            no_bg_image = remove(
                input_image, 
                session=session,
                alpha_matting=True,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=10
            )
            
            st.write("正在应用 1/10 构图标准...")
            final_canvas = Image.new("RGB", (TARGET_W, TARGET_H), BLUE_BG_COLOR)
            orig_w, orig_h = no_bg_image.size
            aspect = orig_w / orig_h
            top_gap = int(TARGET_H * 0.1)
            t_person_h = TARGET_H - top_gap
            t_person_w = int(t_person_h * aspect)
            
            if t_person_w < TARGET_W:
                t_person_w = TARGET_W
                t_person_h = int(t_person_w / aspect)
            
            resized_person = no_bg_image.resize((t_person_w, t_person_h), Image.Resampling.LANCZOS)
            final_canvas.paste(resized_person, ((TARGET_W - t_person_w) // 2, TARGET_H - t_person_h), resized_person)

        elif mode == "半自动模式 (上传透明PNG换底)":
            st.write("直接应用构图标准...")
            no_bg_image = input_image
            final_canvas = Image.new("RGB", (TARGET_W, TARGET_H), BLUE_BG_COLOR)
            orig_w, orig_h = no_bg_image.size
            aspect = orig_w / orig_h
            top_gap = int(TARGET_H * 0.1)
            t_person_h = TARGET_H - top_gap
            t_person_w = int(t_person_h * aspect)
            
            if t_person_w < TARGET_W:
                t_person_w = TARGET_W
                t_person_h = int(t_person_w / aspect)
            
            resized_person = no_bg_image.resize((t_person_w, t_person_h), Image.Resampling.LANCZOS)
            final_canvas.paste(resized_person, ((TARGET_W - t_person_w) // 2, TARGET_H - t_person_h), resized_person)

        elif mode == "仅格式化 (成品图调尺寸/体积)":
            st.write("正在进行无损中心裁剪...")
            final_canvas = ImageOps.fit(
                input_image.convert("RGB"), 
                (TARGET_W, TARGET_H), 
                method=Image.Resampling.LANCZOS, 
                centering=(0.5, 0.5)
            )

        # --- 统一输出与体积优化 ---
        st.write("正在优化文件体积与 DPI...")
        quality = 100
        output_buffer = io.BytesIO()
        
        while quality > 40:
            temp_buffer = io.BytesIO()
            final_canvas.save(temp_buffer, format="JPEG", quality=quality, dpi=(300, 300))
            if temp_buffer.tell() <= 1000 * 1024: # 确保不超过 1MB
                output_buffer = temp_buffer
                if quality >= 95 and temp_buffer.tell() >= 400 * 1024:
                    break
                if quality == 100:
                    break
                break
            quality -= 2
            
        status.update(label="处理完成！", state="complete", expanded=False)

    # --- 结果展示与下载 ---
    col1, col2 = st.columns(2)
    with col1:
        st.image(uploaded_file, caption="原始输入", use_container_width=True)
    with col2:
        st.image(final_canvas, caption="960x1280 高清结果", use_container_width=True)

    st.download_button(
        label="📥 下载高清证件照 (JPG)",
        data=output_buffer.getvalue(),
        file_name="CET_Photo_HD.jpg",
        mime="image/jpeg"
    )
    
    st.success(f"✅ 处理成功！大小: {output_buffer.tell()//1024} KB | 分辨率: 300 DPI")

    # --- 关键：手动清理大变量并触发内存回收 ---
    del input_image
    if 'no_bg_image' in locals(): del no_bg_image
    if 'final_canvas' in locals(): del final_canvas
    gc.collect()
