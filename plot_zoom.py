import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def generate_zoom_plot():
    csv_path = '/home/ubuntu/PROFETA-UNIVERSAL-V5.0/PREVISIONI/real_time_ens_hours.csv'
    
    try:
        df = pd.read_csv(csv_path)
        df = df.sort_values(by='horizon')
        
        # Cerca la colonna con la data/ora reale
        dt_col = None
        if 'timestamp' in df.columns:
            dt_col = 'timestamp'
        elif 'Date' in df.columns:
            dt_col = 'Date'
            
        plt.figure(figsize=(12, 6))
        
        if dt_col:
            # Converte la colonna in vero datetime per matplotlib
            df['plot_time'] = pd.to_datetime(df[dt_col])
            x_data = df['plot_time']
        else:
            x_data = df['horizon']
        
        # Traccia la linea
        plt.plot(x_data, df['predicted_value'], color='#e74c3c', marker='o', markersize=4, linewidth=2.5, label='Previsione Profeta')
        
        # Mappa il minimo assoluto (Target)
        min_idx = df['predicted_value'].idxmin()
        min_point = df.loc[min_idx]
        
        if dt_col:
            min_x = min_point['plot_time']
            # Formatta la stringa per mostrarla bella pulita nell'etichetta
            min_time_str = min_point['plot_time'].strftime('%d %b %H:%M')
        else:
            min_x = min_point['horizon']
            min_time_str = f"+{int(min_point['horizon'])} ore"

        # Stile testuale e griglia
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.title('Zoom estremo: La "Discesa Piatta" scansionata dal Bot (72 Ore)', fontsize=14, fontweight='bold', pad=15)
        plt.xlabel('Data e Ora (Fuso Orario Locale previste)', fontsize=12)
        plt.ylabel('Prezzo Previsto USD ($)', fontsize=12)
        
        # Disegna il puntino target
        plt.scatter([min_x], [min_point['predicted_value']], color='#2c3e50', s=120, zorder=5, label='Target Rilevato')
        
        # Callout testuale del Target
        plt.annotate(
            f'MINIMO RILEVATO\n{min_time_str}\nPrezzo: {min_point["predicted_value"]:.2f}$',
            (min_x, min_point['predicted_value']),
            textcoords="offset points", 
            xytext=(0, 15), 
            ha='center', 
            fontsize=10, 
            fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#2c3e50", alpha=0.9)
        )
        
        # Formatta dinamicamente l'asse X in base al tipo di dati (Datetime o Interi)
        ax = plt.gca()
        if dt_col:
            # Formatta le date sull'asse X (es. 19 Mar 15:00) posizionate ogni 6 ore
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b %H:%M'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
            plt.xticks(rotation=45, ha='right')
        else:
            plt.xticks(range(0, 75, 6))
            
        plt.legend()
        plt.tight_layout()
        
        output_path = '/mnt/c/work/gitrepo/Profeta/zoom_72h.png'
        plt.savefig(output_path, dpi=300)
        print(f"Grafico generato con successo su: {output_path}")
        
    except Exception as e:
        print(f"Errore durante la generazione: {e}")

if __name__ == "__main__":
    generate_zoom_plot()
