# -*- coding: utf-8 -*-
"""Простий генератор іконки для Dota Ready Helper."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def create_simple_icon():
    """Створити просту іконку з літерою D."""
    # Розміри
    size = 512

    # Створити зображення
    img = Image.new('RGBA', (size, size), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Фон - градієнт (імітація)
    for i in range(size):
        alpha = int(255 * (1 - i / size))
        color = (76, 175, 80, 255)  # Зелений
        draw.rectangle([0, i, size, i+1], fill=color)

    # Коло
    margin = 50
    draw.ellipse(
        [margin, margin, size-margin, size-margin],
        fill=(30, 30, 40, 255),
        outline=(76, 175, 80, 255),
        width=10
    )

    # Текст "D"
    try:
        # Спробувати завантажити шрифт
        font = ImageFont.truetype("arial.ttf", 280)
    except:
        # Якщо не вдалось, використати дефолтний
        font = ImageFont.load_default()

    # Намалювати текст
    text = "D"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (size - text_width) // 2 - bbox[0]
    y = (size - text_height) // 2 - bbox[1]

    draw.text((x, y), text, fill=(76, 175, 80, 255), font=font)

    return img

def create_icon_with_shield():
    """Створити іконку зі щитом."""
    size = 512
    img = Image.new('RGBA', (size, size), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Фон
    draw.rectangle([0, 0, size, size], fill=(30, 30, 40, 255))

    # Щит (простий)
    shield_points = [
        (size//2, 50),           # Верх
        (size-100, 150),         # Право верх
        (size-100, 350),         # Право низ
        (size//2, size-50),      # Низ
        (100, 350),              # Ліво низ
        (100, 150),              # Ліво верх
    ]

    draw.polygon(shield_points, fill=(76, 175, 80, 255), outline=(255, 255, 255, 255), width=5)

    # Галочка
    check_points = [
        (180, 280),
        (230, 330),
        (340, 200),
    ]
    draw.line(check_points, fill=(255, 255, 255, 255), width=30, joint='curve')

    return img

def save_icon(img: Image.Image, output_dir: Path):
    """Зберегти іконку у різних форматах."""
    output_dir.mkdir(exist_ok=True)

    # PNG
    png_path = output_dir / "icon.png"
    img.save(png_path, "PNG")
    print(f"OK: Saved {png_path}")

    # ICO (різні розміри)
    ico_path = output_dir / "icon.ico"
    icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, format='ICO', sizes=icon_sizes)
    print(f"OK: Saved {ico_path}")

    return png_path, ico_path

def main():
    """Головна функція."""
    print("=" * 50)
    print("Генератор іконки Dota Ready Helper")
    print("=" * 50)
    print()

    assets_dir = Path(__file__).parent / "assets"

    print("Оберіть варіант:")
    print("1. Проста іконка з літерою D")
    print("2. Іконка зі щитом та галочкою")
    print()

    choice = input("Ваш вибір (1 або 2): ").strip()

    if choice == "1":
        print("\nCreating simple icon...")
        img = create_simple_icon()
    elif choice == "2":
        print("\nCreating shield icon...")
        img = create_icon_with_shield()
    else:
        print("Invalid choice. Using option 1.")
        img = create_simple_icon()

    print("Saving...")
    png_path, ico_path = save_icon(img, assets_dir)

    print()
    print("=" * 50)
    print("SUCCESS: Icon created!")
    print("=" * 50)
    print()
    print(f"PNG: {png_path}")
    print(f"ICO: {ico_path}")
    print()
    print("Now you can build .exe with icon:")
    print("  build_simple.bat")
    print()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nInstall Pillow:")
        print("  pip install Pillow")

    input("\nPress Enter to exit...")
