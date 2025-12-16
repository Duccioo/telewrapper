import argparse
import time
import os
import random
import math


def create_text_files():
    print("📝 Generazione file di testo...")

    # TXT
    filename_txt = f"test_log_{int(time.time())}.txt"
    with open(filename_txt, "w") as f:
        f.write(f"Log generato il {time.ctime()}\n")
        f.write("Questo è un file di testo semplice di prova per Telewrapper.\n")
        f.write("-" * 40 + "\n")
        for i in range(10):
            val = random.random()
            f.write(f"Riga {i+1}: Valore casuale = {val:.4f}\n")
    print(f"   - {filename_txt} creato")

    # Markdown
    filename_md = f"test_report_{int(time.time())}.md"
    with open(filename_md, "w") as f:
        f.write(f"# Report del Test Telewrapper\n\n")
        f.write(f"**Data:** {time.ctime()}\n")
        f.write(f"**Host:** {os.uname().nodename}\n\n")
        f.write("## Risultati Simulazione\n")
        f.write("Ecco una lista di elementi generati:\n")
        for i in range(5):
            f.write(f"- Item {i+1}: Status **OK**\n")
        f.write("\n> Questo è un blocco di citazione Markdown.\n")
    print(f"   - {filename_md} creato")


def create_image_files():
    print("🎨 Generazione immagini...")

    # Generiamo un semplice SVG (Scalable Vector Graphics)
    # Non richiede librerie esterne come PIL/Pillow
    filename_svg = f"test_chart_{int(time.time())}.svg"

    svg_content = f"""
    <svg width="400" height="200" xmlns="http://www.w3.org/2000/svg">
      <!-- Sfondo -->
      <rect width="100%" height="100%" fill="#f0f0f0" />
      
      <!-- Titolo -->
      <text x="200" y="30" font-family="Arial" font-size="20" text-anchor="middle" fill="#333">Telewrapper Test Chart</text>
      
      <!-- Forme geometriche -->
      <circle cx="50" cy="100" r="40" fill="#ff5733" opacity="0.8" />
      <rect x="120" y="60" width="80" height="80" fill="#33ff57" opacity="0.8" />
      <polygon points="250,140 290,60 330,140" fill="#3357ff" opacity="0.8" />
      
      <!-- Timestamp -->
      <text x="390" y="190" font-family="monospace" font-size="10" text-anchor="end" fill="#666">{time.ctime()}</text>
    </svg>
    """

    with open(filename_svg, "w") as f:
        f.write(svg_content.strip())
    print(f"   - {filename_svg} creato")

    # Generiamo un PPM (Portable Pixel Map)
    # È un formato immagine semplice testuale/binario supportato da molti viewer
    filename_ppm = f"test_gradient_{int(time.time())}.ppm"
    width, height = 256, 256

    with open(filename_ppm, "w") as f:
        # Header P3 (ASCII RGB), width, height, max color value
        f.write(f"P3\n{width} {height}\n255\n")
        for y in range(height):
            for x in range(width):
                # Gradiente colorato
                r = x % 256
                g = y % 256
                b = (x + y) % 256
                f.write(f"{r} {g} {b} ")
            f.write("\n")
    print(f"   - {filename_ppm} creato")


def main():
    parser = argparse.ArgumentParser(description="Script di test per Telewrapper")
    parser.add_argument(
        "--text", action="store_true", help="Genera file di testo (.txt, .md)"
    )
    parser.add_argument(
        "--image", action="store_true", help="Genera immagini (.svg, .ppm)"
    )
    parser.add_argument(
        "--duration", type=int, default=10, help="Durata simulazione in secondi"
    )
    parser.add_argument(
        "--fail", action="store_true", help="Simula un fallimento alla fine"
    )

    args = parser.parse_args()

    print(f"🚀 Avvio script di test (PID: {os.getpid()})")
    print(f"⏱  Durata prevista: {args.duration} secondi")
    print("-" * 30)

    # Simulazione lavoro iniziale
    time.sleep(1)

    if args.text:
        create_text_files()

    if args.image:
        create_image_files()

    # Simulazione progresso
    steps = 10
    step_duration = args.duration / steps

    print("\n🔄 Elaborazione in corso...")
    for i in range(steps):
        progress = (i + 1) * 10
        # Simuliamo output variabile
        if i == 3:
            print("   [INFO] Caricamento risorse...")
        elif i == 7:
            print("   [INFO] Ottimizzazione risultati...")

        print(f"   Progress: {progress}%")
        time.sleep(step_duration)

    print("-" * 30)

    if args.fail:
        print("❌ Errore simulato! Qualcosa è andato storto.")
        exit(1)
    else:
        print("✅ Script terminato con successo.")


if __name__ == "__main__":
    main()
