import streamlit as st
from PIL import Image, ImageOps
from rembg import remove, new_session
import io
import gc

# --- 1. 页面配置与性能优化 ---
st.set_page_config(page_title="25级英语考级证件照-全能终极版", layout="centered")

# 每次刷新尝试清理内存
gc.collect()

# 缓存模型加载，避免重复占用资源
@st.cache_resource
def get_rembg_session(model_name):
    return new_session(model_name=model_name)

st.title("🎓 证件照全能工具 (顶配版)")
st.markdown("---")

# --- 2. 侧边栏：多模式与多模型切换 ---
st.sidebar.header("🛠️ 功能面板")

# 模式选择 (芝麻和西瓜都在这)
mode = st.sidebar.radio(
    "选择处理模式：",
    ("全自动 AI 模式 (多模型切换)", 
     "半自动模式 (上传透明PNG换底)", 
     "仅格式化 (成品图调尺寸/体积)")
)

# 只有在全自动模式下才显示模型选择
selected_model_key = "birefnet-portrait"
if mode == "全自动 AI 模式 (多模型切换)":
    st.sidebar.markdown("---")
    st.sidebar.header("🤖 AI 引擎选择")
    model_choice = st.sidebar.selectbox(
        "若效果不好，请切换模型：",
        ("BiRefNet-Portrait (2024最强人像)", 
         "ISNet (侧重发丝细节)", 
         "U2Net (侧重衣服整体稳定性)")
    )
    
    # 映射模型内部名称
    model_map = {
        "BiRefNet-Portrait (2024最强人像)": "birefnet-portrait",
        "ISNet (侧重发丝细节)": "isnet-general-use",
        "U2Net (侧重衣服整体稳定性)": "u2net"
    }
    selected_model_key = model_map[model_choice]
    st.sidebar.warning("提示：首次使用新模型需下载(约100-300MB)，请耐心等待片刻。")

st.sidebar.markdown("---")
st.sidebar.info("规格锁定：960x1280 | 300 DPI | 约 500KB | 顶部留空 1/10")

# --- 3. 核心参数定义 ---
TARGET_W, TARGET_H = 960, 1280
BLUE_BG_COLOR = (67, 142, 219)

# --- 4. 文件上传逻辑 ---
if mode == "全自动 AI 模式 (多模型切换)":
    tip = "直接拖入原始照片"
elif mode == "半自动模式 (上传透明PNG换底)":
    tip = "直接拖入你在 PS 中扣好的透明 PNG"
else:
    tip = "直接拖入已有蓝底照 (仅修正规格)"

uploaded_file = st.file_uploader(tip, type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    with st.status("正在按照专业规格处理中...", expanded=True) as status:
        
        # 加载图像并转为 RGBA 模式
        input_image = Image.open(uploaded_file).convert("RGBA")
        final_canvas = None 

        # ================= 逻辑分支 =================

        # --- 模式 A：全自动 AI ---
        if mode == "全自动 AI 模式 (多模型切换)":
            st.write(f"正在启动 {selected_model_key} 引擎进行精准抠像...")
            session = get_rembg_session(selected_model_key)
            
            # 只有 ISNet 模式开启额外的发丝羽化
            use_alpha = True if "isnet" in selected_model_key else False
            
            no_bg_image = remove(
                input_image, 
                session=session,
                alpha_matting=use_alpha,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=10
            )
            
            st.write("应用 1/10 顶部留空构图标准...")
            final_canvas = Image.new("RGB", (TARGET_W, TARGET_H), BLUE_BG_COLOR)
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

        # --- 模式 B：半自动 (透明PNG) ---
        elif mode == "半自动模式 (上传透明PNG换底)":
            st.write("跳过 AI，直接使用上传的透明层...")
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
            
            resized = no_bg_image.resize((t_person_w, t_person_h), Image.Resampling.LANCZOS)
            final_canvas.paste(resized, ((TARGET_W - t_person_w) // 2, TARGET_H - t_person_h), resized)

        # --- 模式 C：仅格式化 ---
        elif mode == "仅格式化 (成品图调尺寸/体积)":
            st.write("执行无损中心裁剪与像素对齐...")
            final_canvas = ImageOps.fit(
                input_image.convert("RGB"), 
                (TARGET_W, TARGET_H), 
                method=Image.Resampling.LANCZOS, 
                centering=(0.5, 0.5)
            )

        # ================= 统一输出控制 =================
        st.write("正在优化高清体积 (目标 500KB+)...")
        quality = 100
        output_buffer = io.BytesIO()
        
        while quality > 40:
            temp = io.BytesIO()
            final_canvas.save(temp, format="JPEG", quality=quality, dpi=(300, 300))
            if temp.tell() <= 1000 * 1024:
                output_buffer = temp
                # 质量 95 以上且大小超过 400K 即可视为完美
                if quality >= 95 and temp.tell() >= 400 * 1024:
                    break
                if quality == 100: break
                break
            quality -= 2
            
        status.update(label="全部处理完成！", state="complete")

    # --- 结果展示 ---
    col1, col2 = st.columns(2)
    with col1: st.image(uploaded_file, caption="原始输入", use_container_width=True)
    with col2: st.image(final_canvas, caption="960x1280 高清预览", use_container_width=True)

    st.download_button(
        label="📥 下载最终高清证件照 (JPG)",
        data=output_buffer.getvalue(),
        file_name="CET_FINAL_PHOTO.jpg",
        mime="image/jpeg"
    )
    
    st.success(f"✅ 处理成功！体积: {output_buffer.tell()//1024} KB | 分辨率: 300 DPI")
    
    # 释放内存
    del input_image
    if 'no_bg_image' in locals(): del no_bg_image
    if 'final_canvas' in locals(): del final_canvas
    gc.collect()
