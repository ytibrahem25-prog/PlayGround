# Ibrahim Amer Minecraft — لعبة 3D مكعبات (Python + Kivy)

© Ibrahim Amer — اسم اللعبة: **Ibrahim Amer Minecraft**

لعبة 3D بأسلوب Minecraft: عالم فوكسل، حركة وقفز، تدوير كاميرا باللمس،
كسر/وضع بلوكات، 5 أنواع بلوكات (Grass / Dirt / Stone / Wood / Leaves)،
أزرار موبايل واضحة. تعمل على **الديسكتوب** وتتحول إلى **APK** عبر Buildozer.

## التشغيل على الديسكتوب

```bash
cd ibrahim-amer-minecraft
pip install -r requirements.txt
python main.py
```

تحكم الديسكتوب:
- `WASD` / الأسهم = حركة، `Space` = قفز
- سحب الماوس = تحريك الكاميرا
- كليك يسار = كسر، كليك يمين = وضع، `1-5` = اختيار بلوك، `B`/`P` = كسر/وضع

تحكم الموبايل:
- D-pad يسار = حركة، سحب الشاشة = كاميرا
- زر `⬆ قفز` للقفز، `⛏ كسر` / `🧱 وضع` للبناء، الشريط السفلي لاختيار البلوك

## التحويل إلى APK (Android)

```bash
pip install buildozer
buildozer android debug
# الملف الناتج في bin/*.apk — ثبّته على هاتفك
```

المتطلبات: Linux + Java 17 + Android SDK (Buildozer يجهزها تلقائيًا أول مرة).

## الملفات

| ملف | الوصف |
|---|---|
| `main.py` | تطبيق Kivy: العرض 3D + HUD + أزرار اللمس + حقوق © Ibrahim Amer |
| `world.py` | بيانات الفوكسل + توليد العالم + raycast + فيزياء (بدون Kivy) |
| `renderer.py` | إسقاط 3D→2D + أوجه المكعب (بدون Kivy) |
| `buildozer.spec` | إعدادات APK (الاسم Ibrahim Amer Minecraft) |
| `requirements.txt` | `Kivy>=2.3.0` |

## ملاحظات تقنية

- عرض 3D مخصص عبر Kivy Canvas (painter's algorithm + إسقاط منظور) — يعمل على
  OpenGL ES في أندرويد بدون مكتبات native إضافية.
- مسافة العرض 11 بلوك، فيزياء جاذبية وقفز وتصادم AABB لكل محور.
- استهداف البلوك عبر DDA raycast حتى 6 بلوكات.
