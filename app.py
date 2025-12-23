import streamlit as st
from PIL import Image, ImageOps
from rembg import remove, new_session
import io
import gc

# --- 1. 页面配置与内存回收 ---
st.set_page_config(page_title="高清证件照-支持拖拽上传", layout="centered")
gc.collect() 

# 自定义 CSS 让上传框更大、更醒目，方便拖拽
st.markdown("""
    <style>
    .stFileUploader {
        border: 2px dashed #4286db;
        border-radius: 10px;
        padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📸 专业证件照工具 (支持直接拖入图片)")
st.markdown("---")

# --- 2. 初始化 AI 模型 (带缓存) ---
@st.cache_resource
def get_rembg_session(model_name):
    return new_session(model_name=model_name)

# --- 3. 侧边栏设置 ---
st.sidebar.header("🚀 功能与模型选择")
mode = st.sidebar.radio(
    "处理模式：",
    ("全自动 AI 模式", "半自动 (上传透明PNG)", "仅格式化尺寸")
)

ai_model = "isnet-general-use"
if mode == "全自动 AI 模式":
    model_type = st.sidebar.selectbox(
        "如果衣服/肩膀被误删，请切换模型：",
        ("发丝优化 (ISNet)", "整体稳定 (U2Net)")
    )
    ai_model = "isnet-general-use" if "ISNet" in model_type else "u2net"

st.sidebar.markdown("---")
st.sidebar.info("规格：960x1280 | 300 DPI | ~500KB")

# --- 4. 核心参数 ---
TARGET_W, TARGET_H = 960, 1280
BLUE_BG = (67, 142, 219)

# --- 5. 文件上传 (原生支持拖拽) ---
# label 留空，使用 markdown 自定义提示
st.markdown("### 📥 请将图片直接**拖到下方框内**或点击上传")
uploaded_file = st.file_uploader("", type=["jpg", "jpeg", "png"], help="支持从电脑文件夹或微信窗口直接拖入")

if uploaded_file is not None:
    with st.status("正在处理图片，请稍候...", expanded=True) as status:
        # 加载
        input_image = Image.open(uploaded_file).convert("RGBA")
        
        # --- 模式处理 ---
        if mode == "全自动 AI 模式":
            st.write(f"正在使用 {ai_model} 模型抠图...")
            session = get_rembg_session(ai_model)
            # 根据模型特性微调参数
            is_isnet = "isnet" in ai_model
            no_bg_image = remove(
                input_image, 
                session=session,
                alpha_matting=is_isnet, # ISNet 开启羽化，U2Net 关闭
                alpha_matting_foreground_threshold=240 if is_isnet else 270
            )
        elif mode == "半自动 (上传透明PNG)":
            no_bg_image = input_image
        else: # 仅格式化
            no_bg_image = None

        # --- 构图生成 ---
        if no_bg_image:
            st.write("正在应用 1/10 构图标准...")
            final_canvas = Image.new("RGB", (TARGET_W, TARGET_H), BLUE_BG)
            orig_w, orig_h = no_bg_image.size
            aspect = orig_w / orig_h
            top_gap = int(TARGET_H * 0.1)
            t_person_h = TARGET_H - top_gap
            t_person_w = int(t_person_h * aspect)
            
            if t_person_w < TARGET_W:
                t_person_w = TARGET_W
                t_person_h = int(t_person_w / aspect)
            
            resized = no_bg_image.resize((t_person_w, t_person_h), Image.Resampling.LANCZOS)
            final_canvas.paste(resized, ((TARGET_W - t_person_w) // 2, TARGET_H - t_person_h), resized)
        else:
            st.write("正在进行无损中心裁剪...")
            final_canvas = ImageOps.fit(input_image.convert("RGB"), (TARGET_W, TARGET_H), method=Image.Resampling.LANCZOS)

        # --- 质量压缩 ---
        st.write("优化文件体积...")
        quality = 100
        output_buffer = io.BytesIO()
        while quality > 40:
            temp = io.BytesIO()
            final_canvas.save(temp, format="JPEG", quality=quality, dpi=(300, 300))
            if temp.tell() <= 1000 * 1024:
                output_buffer = temp
                if quality >= 95 and temp.tell() >= 400 * 1024: break
                break
            quality -= 2
            
        status.update(label="处理完成！", state="complete")

    # --- 展示与下载 ---
    col1, col2 = st.columns(2)
    with col1: st.image(uploaded_file, caption="原始输入", use_container_width=True)
    with col2: st.image(final_canvas, caption="960x1280 预览", use_container_width=True)

    st.download_button(
        label="📥 下载高清证件照",
        data=output_buffer.getvalue(),
        file_name="Standard_Photo_HD.jpg",
        mime="image/jpeg"
    )
    
    st.success(f"✅ 大小: {output_buffer.tell()//1024} KB | 分辨率: 300 DPI")
    
    # 彻底清理内存
    del input_image
    if 'no_bg_image' in locals(): del no_bg_image
    if 'final_canvas' in locals(): del final_canvas
    gc.collect()
