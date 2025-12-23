import streamlit as st
from PIL import Image, ImageOps
from rembg import remove, new_session
import io
import gc

# --- 1. 页面与内存优化 ---
st.set_page_config(page_title="25级考级-顶配版", layout="centered")

@st.cache_resource
def get_session(model_name):
    # 如果内存还是报错，建议在这里指定使用 birefnet-portrait 
    # 它是专门为人像优化的轻量高清模型
    return new_session(model_name=model_name)

st.title("📸 顶配证件照工具 (BiRefNet 模型)")

# --- 2. 侧边栏：模型升级 ---
st.sidebar.header("🤖 模型实验室")
model_choice = st.sidebar.selectbox(
    "选择最强抠图模型：",
    ("BiRefNet-Portrait (2024最强人像)", 
     "RMBG-1.4 (专业级背景移除)", 
     "ISNet (经典发丝版)",
     "U2Net (整体稳定版)")
)

# 映射内部名称
model_map = {
    "BiRefNet-Portrait (2024最强人像)": "birefnet-portrait",
    "RMBG-1.4 (专业级背景移除)": "briaai/rmbg-1.4",
    "ISNet (经典发丝版)": "isnet-general-use",
    "U2Net (整体稳定版)": "u2net"
}

st.sidebar.info("💡 BiRefNet 对发丝和衣服边缘的识别度更高，强烈推荐。")

# --- 3. 核心规格 ---
T_W, T_H = 960, 1280
BLUE = (67, 142, 219)

# --- 4. 处理逻辑 ---
uploaded_file = st.file_uploader("拖入你的照片", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    try:
        with st.status("正在使用顶级 AI 运算...", expanded=True) as status:
            img = Image.open(uploaded_file).convert("RGBA")
            
            st.write(f"正在加载 {model_choice}...")
            sess = get_session(model_map[model_choice])
            
            # 使用新模型进行抠图
            # 对 BiRefNet 我们关闭 alpha_matting，因为它内置的边缘处理已经很强了
            no_bg = remove(img, session=sess)
            
            st.write("正在校准 960x1280 高清构图...")
            canvas = Image.new("RGB", (T_W, T_H), BLUE)
            w, h = no_bg.size
            # 锁定 1/10 顶部留空
            scale = (T_H * 0.9) / h
            nw, nh = int(w * scale), int(h * scale)
            if nw < T_W:
                nw = T_W
                nh = int(nw * (h/w))
            
            resized = no_bg.resize((nw, nh), Image.Resampling.LANCZOS)
            canvas.paste(resized, ((T_W - nw)//2, T_H - nh), resized)
            
            # 保存
            out = io.BytesIO()
            canvas.save(out, format="JPEG", quality=98, dpi=(300, 300))
            status.update(label="处理完成！", state="complete")

        st.image(canvas, use_container_width=True)
        st.download_button("📥 下载 500KB+ 高清照", out.getvalue(), "HD_Photo.jpg", "image/jpeg")
        
        # 内存回收
        del img, canvas, no_bg
        gc.collect()

    except Exception as e:
        st.error(f"内存又爆了！请点击侧边栏 Manage App -> Reboot。错误信息: {e}")
