import streamlit as st
import pandas as pd
import io
from sqlalchemy import create_engine
from api import search_europe_price, get_tcmb_rates

# 11. Gün: Arayüz İyileştirmeleri ve Kurumsal Görünüm
st.set_page_config(page_title="Trio Bilişim - Avrupa Yedek Parça Tedarik Sistemi", layout="wide")

# 2. ve 7. Gün: Veritabanı Tasarımı ve Entegrasyonu
# SQLAlchemy ile SQLite kullanılarak log kayıtlarının tutulacağı bir veritabanı bağlantısı
engine = create_engine('sqlite:///trio_yedek_parca_sistemi.db', echo=False)

# 4. Gün: Streamlit ile Temel Arayüz Geliştirmeleri
st.title("Trio Bilişim - Yedek Parça Tedarik ve Analiz Sistemi")
st.markdown("---")
st.info("Bu sistem, yurt dışı (Avrupa) tedarik ağlarından orijinal (Sıfır/OEM) yedek parça fiyatlarını tarar ve TCMB anlık kurlarıyla TL analizi yapar. İkinci el ürünler sistem tarafından otomatik filtrelenmektedir.")

# 8. Gün: TCMB Verileriyle Dinamik Kur Hesaplaması
rates = get_tcmb_rates()
st.write(f"📈 **Anlık TCMB Kurları:** 1 EUR = **{rates.get('EUR', 'Hata')} ₺** | 1 USD = **{rates.get('USD', 'Hata')} ₺**")

st.markdown("### Parça Sorgulama Ekranı")
part_code = st.text_input("Tedarik Edilecek Parça Kodunu Girin (Örn: L12345-001):")

if st.button("Fiyat Analizini Başlat"):
    if part_code.strip():
        with st.spinner("Avrupa distribütör ağı taranıyor, filtrelemeler yapılıyor..."):
            
            # API'den sonuçları çek
            data = search_europe_price(part_code)
            
            if data:
                df = pd.DataFrame(data)
                
                # 9. Gün: Fiyat Analizi ve Karşılaştırma Algoritması
                # TL fiyatına göre ucuzdan pahalıya sıralama
                df = df.sort_values(by="Fiyat (TL)", ascending=True)
                
                st.success(f"Analiz tamamlandı! '{part_code}' için en uygun fiyatlı Avrupa tedarikçileri listelendi.")
                
                # 7. Gün: Çekilen verileri SQL veritabanına kaydet (Log tutma ve Dinamik İşlem)
                try:
                    df.to_sql('avrupa_arama_loglari', con=engine, if_exists='append', index=False)
                except Exception as e:
                    pass
                
                # Tıklanabilir Linkler ve Kurumsal Görünüm
                st.dataframe(
                    df,
                    column_config={
                        "Satın Alma Linki": st.column_config.LinkColumn(
                            "Satın Alma Linki",
                            display_text="İlana Git ↗" 
                        ),
                        "Fiyat (TL)": st.column_config.NumberColumn(
                            "Fiyat (TL)",
                            format="%.2f ₺"
                        ),
                        "Fiyat (EUR)": st.column_config.NumberColumn(
                            "Fiyat (EUR)",
                            format="%.2f €"
                        )
                    },
                    hide_index=True, 
                    use_container_width=True 
                )
                
                # 10. Gün: Excel Çıktı Alma Özelliğinin Eklenmesi
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Trio_Fiyat_Analizi')
                processed_data = output.getvalue()
                
                st.download_button(
                    label="📥 Analiz Raporunu Excel Olarak İndir",
                    data=processed_data,
                    file_name=f"{part_code}_Avrupa_Tedarik_Raporu.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("Bu parça kodu için Avrupa pazarında Sıfır/OEM onayı olan bir fiyat bulunamadı. Lütfen kodu kontrol edin.")
    else:
        st.error("Lütfen geçerli bir parça kodu girin!")