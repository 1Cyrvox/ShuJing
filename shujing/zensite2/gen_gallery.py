import os
from collections import OrderedDict

films = [
    ("quadratic-formula", "二次公式", "配方将方程变成图画。每一项保持自己的颜色，矩形移动，二次公式从中浮现。", "QuadraticFormula-3d04a701937060e1a82a.webp", "quadratic_formula.py", "方程与证明"),
    ("pythagoras", "勾股定理：重排证明", "移动四个直角三角形，揭示为什么 a² + b² = c²。三角形及其外接正方形面积始终不变。", "Pythagoras-f116950052dc5fa8abb5.webp", "pythagoras.py", "方程与证明"),
    ("circle-area", "展开圆周", "薄环展开成条带，堆叠成三角形。底为 2πr，高为 r，面积即 πr²。", "CircleArea-344171e19a2c0199ff91.webp", "circle_area.py", "方程与证明"),
    ("euler-identity", "欧拉恒等式：一次漫步", "指数级数的各项在复平面中螺旋趋近 −1。让角度变化，它们的和沿单位圆环行。", "EulerIdentity-4aee10662b75316cae13.webp", "euler_identity.py", "方程与证明"),
    ("derivative", "导数度量什么", "曲线上两点靠近时，割线变成切线。切线斜率的变化描出导数的图像。", "DerivativeSlope-a9d6a1e78e3e23f4e98a.webp", "derivative.py", "微积分"),
    ("riemann-sums", "矩形变成积分", "更薄的矩形让和更接近曲线下方的面积。每次细分劈开矩形，更新测量面积。", "RiemannSums-ec9b77096de10f38a6e7.webp", "riemann_sums.py", "微积分"),
    ("taylor-series", "多项式变成正弦", "每个新的泰勒项让多项式跟上更多正弦波。增长的公式和图像一起变化。", "TaylorSeries-9278328e9e54e6278d32.webp", "taylor_series.py", "微积分"),
    ("unit-circle", "圆画出正弦和余弦", "旋转的半径从高度和跨度描出正弦和余弦。圆内接的直角三角形也说明 sin²θ + cos²θ = 1。", "UnitCircle-5a2c362a3ad9a5828e9b.webp", "unit_circle.py", "微积分"),
    ("linear-maps", "矩阵移动平面", "矩阵带着网格、基向量箭头和单位正方形一起移动。行列式度量平面在剪切、旋转、压扁和翻转时面积的变化。", "LinearMaps-45b05423c40486c6df21.webp", "linear_maps.py", "平面与曲面"),
    ("complex-maps", "复函数弯曲平面", "网格在 z²、指数和正弦下弯曲。直线变成抛物线、圆和射线，每个点走向它的像。", "ComplexMaps-895e17a401f9605285d8.webp", "complex_maps.py", "平面与曲面"),
    ("surface-plots", "公式生成地貌", "平坦的网格升成蛋盒、马鞍和钟形。每个曲面由公式计算，随相机转动弯入下一个。", "SurfacePlots-6c238631ff0bface8cca.webp", "surface_plots.py", "平面与曲面"),
    ("fourier-pi", "圆画出 π", "旋转箭头链描出 π 的轮廓。箭头的长度和相位来自字母的傅里叶系数，相机跟随笔尖拉近观看。", "FourierPi-4eb7b9d113479a9b8d4c.webp", "fourier_pi.py", "图案与惊奇"),
    ("times-tables", "圆上的乘法表", "将圆周上的数连接到其倍数，画出心脏线和其他曲线。连续改变乘数让图案转动、分裂和折叠。", "TimesTables-1ee83b3f84e516e3245d.webp", "times_tables.py", "图案与惊奇"),
    ("colliding-blocks", "两块数 π", "两块和墙之间的弹性碰撞数出 π 的位数。每次碰撞都是模拟的，质量比决定出现多少位数字。", "CollidingBlocks-c9d319bc895e00c90edd.webp", "colliding_blocks.py", "图案与惊奇"),
    ("prime-spirals", "素数螺旋", "将素数画在距离 p、角度 p 处，显现螺旋，相机拉远时变成射线。", "PrimeSpirals-3ddcfb31ef2c5de6eaac.webp", "prime_spirals.py", "图案与惊奇"),
    ("hilbert-curve", "希尔伯特空间填充曲线", "路径访问越来越细的方格的每个单元格。四份较小的副本，旋转并连接，构成下一阶希尔伯特曲线。", "HilbertCurve-1f08eaaed4ca6898c4aa.webp", "hilbert_curve.py", "图案与惊奇"),
    ("galton-board", "高尔顿板", "反复的左右弹跳堆出钟形球堆。测量的计数趋近钉子下方的二项分布。", "GaltonBoard-7e6d521a2268d9864161.webp", "galton_board.py", "图案与惊奇"),
    ("lorenz-attractor", "洛伦兹吸引子", "八个几乎相同的起点描出蝴蝶然后散开。两条路径都遵循洛伦兹方程，展示确定性系统如何混沌。", "LorenzAttractor-101ff9d377d0288d34e9.webp", "lorenz_attractor.py", "图案与惊奇"),
    ("hopf-fibration", "霍普夫纤维化", "三维球面由圆组成，每两个圆恰好链接一次。每个圆位于普通球面的一点之上，影片度量每对圆的链接数。", "HopfFibration-c66662e1ed77f99996dd.webp", "hopf_fibration.py", "几何与拓扑"),
    ("clifford-torus", "翻转圆环面", "四维中的四分之一圈把圆环面翻转过来。中途它穿过无穷远，变成带柄的平面。", "CliffordTorus-ec7c219663dc06e92979.webp", "clifford_torus.py", "几何与拓扑"),
    ("catenoid-helicoid", "不拉伸的弯曲", "螺旋面卷成悬链面而不拉伸。每一步的距离和曲率保持不变（高斯绝妙定理）。", "CatenoidHelicoid-e2f050576cac4c786c80.webp", "catenoid_helicoid.py", "几何与拓扑"),
    ("kaleidoscope-sphere", "球面上的万花筒", "三面镜子用 120 个三角形铺满球面。一个点及其反射生成正二十面体、正十二面体和介于其间的多面体。", "KaleidoscopeSphere-98fb5c5d534f5b8c8c1f.webp", "kaleidoscope_sphere.py", "几何与拓扑"),
    ("menger-slice", "门格海绵中的星", "沿中心切开，门格海绵满是六角星。切面沿长对角线，是一个六边形。", "MengerSlice-f0fce1231b0b15e8af71.webp", "menger_slice.py", "几何与拓扑"),
    ("lozenge-cubes", "立方体与北极圈", "菱形的随机铺砌是沿对角线看到的立方体堆。圆外铺砌冻结。", "LozengeCubes-adbb45375e5469b7a3d0.webp", "lozenge_cubes.py", "几何与拓扑"),
    ("riemann-surfaces", "√z 住在哪里", "平方根绕 0 一圈后变号，所以它住在两张面上。对数每圈攀升：无尽的阶梯。", "RiemannSurfaces-6dc385ddcc6c437a18f7.webp", "riemann_surfaces.py", "几何与拓扑"),
    ("rupert-cube", "鲁珀特立方体", "一个立方体可以穿过相同立方体上的孔（鲁珀特，1693）。", "RupertCube-afbb8c0b7c4f68c80e9a.webp", "rupert_cube.py", "几何与拓扑"),
    ("taylor-poles", "泰勒级数为何停止", "1/(1 + x²) 的泰勒级数在 |x| = 1 处停止收敛。±i 处的两个极点是原因。", "TaylorPoles-650476234d0e7564064a.webp", "taylor_poles.py", "几何与拓扑"),
    ("voronoi-cones", "晶体与锥", "Voronoi 单元是从种子长出的晶体。从上方看，它们也是一片锥的田野。", "VoronoiCones-a63353ad875481916fd5.webp", "voronoi_cones.py", "几何与拓扑"),
    ("bifurcation-mandelbrot", "芒德布罗集中的倍周期", "逻辑映射的倍周期从芒德布罗集中升起。每次倍周期坐在两个球之间的夹点上。", "BifurcationMandelbrot-51eb27f4d1bc67459e1c.webp", "bifurcation_mandelbrot.py", "几何与拓扑"),
    ("sugihara-cylinder", "圆还是方？", "管口从正面看是圆，在镜中是方（杉原，2016）。它是一条三维曲线，从两个视图解出。", "SugiharaCylinder-c8daa7813d5b48cb4077.webp", "sugihara_cylinder.py", "几何与拓扑"),
    ("sphere-packing", "堆橙子", "橙子有两种堆法，一种是立方体站在角上。一刀切过两堆测出各占 74.05% 空间。", "SpherePacking-519a33bac46b9c04c993.webp", "sphere_packing.py", "几何与拓扑"),
    ("heavy-top", "陀螺", "陀螺不倒：它进动和点头。尖端描出尖点、环或波，取决于如何启动。", "HeavyTop-f754f341db2e62ca9d3b.webp", "heavy_top.py", "物理"),
    ("tennis-racket", "网球拍翻转", "绕中间轴旋转的柄反复翻转（贾尼别科夫效应）。恒定能量的曲线说明了原因。", "TennisRacket-2304a2234fdd499bb37e.webp", "tennis_racket.py", "物理"),
    ("lagrange-points", "拉格朗日点", "随地球和月球转动的视角中，拉格朗日点 L4 和 L5 是山顶。然而科里奥利力让探测器停在其上。", "LagrangePoints-a2bc29575f9a383ebf50.webp", "lagrange_points.py", "物理"),
    ("van-allen", "范艾伦辐射带", "带电粒子在地球磁场中旋转、弹跳和漂移。磁场是一个磁瓶，它困住了辐射带。", "VanAllen-d919f751fd36a581bd6e.webp", "van_allen.py", "物理"),
    ("vortex-rings", "跳蛙烟环", "两个烟环轮流穿过对方（亥姆霍兹，1858）。开尔文冲量 r₁² + r₂² 保持不变。", "VortexRings-791d6cc1197534804d7f.webp", "vortex_rings.py", "物理"),
    ("wave-packet", "量子隧穿", "量子粒子穿过它经典上无法越过的墙。测量的透射率与公式吻合。", "WavePacket-9d7f4170da6bcc9ed254.webp", "wave_packet.py", "物理"),
    ("cherenkov-cone", "切连科夫光", "在水中比光还快的电荷留下一锥蓝光。影片测量锥角并与公式比较。", "CherenkovCone-4921f751e8e8ae6e7bfdb.webp", "cherenkov_cone.py", "物理"),
    ("turing-torus", "环面上的图灵图案", "两种化学物质在甜甜圈上反应和扩散，画上斑点和条纹（Gray–Scott；图灵，1952）。", "TuringTorus-900ce89f41226f955b4b.webp", "turing_torus.py", "物理"),
    ("kuramoto-fireflies", "萤火虫同步", "超过临界耦合后，2000 只萤火虫步调一致。同步程度与精确曲线吻合。", "KuramotoFireflies-3f2139672c552561140b.webp", "kuramoto_fireflies.py", "物理"),
    ("dla-coral", "随机游走的珊瑚", "18000 个随机游走者游荡直到碰到集群并粘住。它们建出的珊瑚分形维数 2.5。", "DlaCoral-29e75534911d8d6ec608.webp", "dla_coral.py", "物理"),
    ("phased-array", "用相位控制波束", "固定天线仅靠相位控制波束方向。影片展示实时波场，然后是三维波束。", "PhasedArray-eab9345a50fcbbb23216.webp", "phased_array.py", "工程"),
    ("miura-ori", "三浦折叠", "一拉折起整张纸，没有面弯曲。它同时向两个方向打开（负泊松比）。", "MiuraOri-f7b29345bad91b8957a3.webp", "miura_ori.py", "工程"),
    ("harmonic-drive", "谐波驱动", "谐波波齿轮在一个扁平环中实现 30:1 减速。60 齿的柔环在 62 齿的环内，每转退两齿。", "HarmonicDrive-3fc190352f7c61688556.webp", "harmonic_drive.py", "工程"),
    ("traffic-helix", "无中生有的堵车", "以时间为第三维，堵车是路径的结。每辆车前进时，堵车波后退。", "TrafficHelix-88ebbc2d9a4178f8f0f4.webp", "traffic_helix.py", "工程"),
    ("score-diffusion", "噪声变成文字", "噪声沿数据的精确分数流变成文字。这是一个没有神经网络的扩散模型。", "ScoreDiffusion-24cc468b055052ddf9c7.webp", "score_diffusion.py", "计算与学习"),
    ("neural-untangle", "网络解开螺旋", "一个小网络在场景开始时训练，把一条螺旋抬到另一条之上。然后一个平面分开它们。", "NeuralUntangle-ff7024f0e55f8fd9ef4f.webp", "neural_untangle.py", "计算与学习"),
    ("life-spacetime", "时空中的生命游戏", "堆叠生命游戏的各代，滑翔机枪的滑翔机变成阶梯。它们以 c/4 攀升。", "LifeSpacetime-b0e80e9f5f2e6881dc8d.webp", "life_spacetime.py", "计算与学习"),
]

examples_dir = '../../examples'

groups = OrderedDict()
for slug, title, desc, webp, py, group in films:
    if group not in groups:
        groups[group] = []
    groups[group].append((slug, title, desc, webp, py))

lines = [
    "---",
    "title: 画廊",
    "description: 数境动画作品画廊 — 48 个精选数学动画",
    "---",
    "",
    "# 画廊",
    "",
    "四十八部用数境（ManimGX）制作的短片，每个都是一个只需 numpy 的 Python 文件。屏幕上的每个数字都在影片播放时实时计算。",
    "",
]

for group, items in groups.items():
    lines.append(f"## {group}")
    lines.append("")
    lines.append('<div class="grid cards mx-cards" markdown>')
    lines.append("")
    for slug, title, desc, webp, py in items:
        lines.append(f'-   ![](../films/{webp})')
        lines.append("")
        lines.append(f'    [**{title}**]({slug}.md)')
        lines.append("")
        lines.append(f'    {desc}')
        lines.append("")
    lines.append("</div>")
    lines.append("")

with open('content/gallery/index.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

for slug, title, desc, webp, py, group in films:
    py_path = os.path.join(examples_dir, py)
    with open(py_path, 'r', encoding='utf-8') as f:
        source_code = f.read()

    page = "---\n"
    page += f"title: {title}\n"
    page += f"description: {desc}\n"
    page += "---\n\n"
    page += f"# {title}\n\n"
    page += f"{desc}\n\n"
    mp4 = webp.replace('.webp', '.mp4')
    page += '<div class="mx-example">\n\n'
    page += f'<video class="mx-film" src="/films/{mp4}" poster="/films/{webp}" muted loop playsinline controls preload="none"></video>\n\n'
    page += '<details class="mx-code">\n'
    page += f'<summary>examples/{py}</summary>\n\n'
    page += "```python\n"
    page += source_code.rstrip() + "\n"
    page += "```\n\n"
    page += "</details>\n\n"
    page += "</div>\n"

    with open(f'content/gallery/{slug}.md', 'w', encoding='utf-8') as f:
        f.write(page)

print(f"Done: gallery index + {len(films)} film pages")