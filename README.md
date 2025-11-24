# Görev Yöneticisi - Basit Flask Örneği

Bu proje, sağladığınız HTML taslağına göre hazırlanmış basit bir Flask uygulamasıdır. Amaç: arkadaşlarınızın da çalıştırıp inceleyebileceği profesyonel ve minimal bir yapı sunmak.

Örnek çalışma adımları (Windows PowerShell):

1. Sanal ortam oluşturun ve aktifleştirin

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Bağımlılıkları yükleyin

```powershell
pip install -r requirements.txt
```

3. Uygulamayı çalıştırın

```powershell
python app.py
```

4. Tarayıcıda açın: http://127.0.0.1:5000/

Dosyalar:
- `templates/base.html` : Genel sayfa düzeni, side-nav ve include'lar
- `templates/_header.html` : Sayfa üst bilgisi (karşılama ve hızlı ekle düğmesi)
- `templates/_footer.html` : Sayfa altbilgisi
- `templates/index.html` : Ana sayfa içeriği (istatistik kartları)
- `app.py` : Basit Flask uygulaması

İleri adımlar önerisi: kullanıcı kimlik doğrulama, veritabanı (sqlite/SQLAlchemy), görev CRUD işlemleri ve statik dosyalar için optimize edilmiş yapı.
