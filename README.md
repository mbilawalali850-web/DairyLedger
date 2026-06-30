# 🥛 DairyLedger — Android Application

**Version:** 1.0  
**Platform:** Android 8.0 (API 26)+  
**Architecture:** MVVM + Room + Coroutines  
**Language:** Kotlin

---

## Project Structure

```
app/src/main/java/com/dairyledger/
│
├── data/
│   ├── local/
│   │   ├── entities/          ← Room database tables
│   │   │   ├── Customer.kt
│   │   │   ├── MilkEntry.kt
│   │   │   ├── Payment.kt
│   │   │   └── RateChart.kt
│   │   ├── dao/               ← Database access objects (queries)
│   │   │   ├── CustomerDao.kt
│   │   │   ├── MilkEntryDao.kt
│   │   │   ├── PaymentDao.kt
│   │   │   └── RateChartDao.kt
│   │   └── DairyLedgerDatabase.kt  ← Room DB singleton
│   └── repository/            ← Data access layer (used by ViewModels)
│       ├── CustomerRepository.kt
│       └── MilkEntryRepository.kt
│
├── domain/
│   └── usecase/
│       └── MilkStandardCalculator.kt  ← SNF formula, rate calculation
│
├── presentation/
│   ├── ui/                    ← Fragments / Activities
│   │   ├── dashboard/         ← Main screen
│   │   ├── customer/          ← Customer profile & list
│   │   ├── milkentry/         ← Data entry form
│   │   ├── payment/           ← Payment logging
│   │   └── report/            ← Report generation screen
│   └── viewmodel/
│       ├── DashboardViewModel.kt
│       └── MilkEntryViewModel.kt
│
└── utils/
    ├── WhatsAppHelper.kt      ← WhatsApp bill message sender
    └── ExcelExporter.kt       ← .xlsx report generation
```

---

## Setup Instructions

### 1. Open in Android Studio
Open the `DairyLedger/` folder in Android Studio Hedgehog (2023.1.1) or newer.

### 2. Sync Gradle
Let Android Studio sync dependencies from `app/build.gradle`.

### 3. Key Dependencies
| Library | Purpose |
|---|---|
| Room 2.6.1 | Local SQLite database |
| Lifecycle / LiveData | MVVM architecture |
| Kotlin Coroutines | Async DB operations |
| Apache POI 5.2.3 | Excel (.xlsx) export |
| Navigation Component | Fragment navigation |

### 4. Still Needed (TODO)
- [ ] `MainActivity.kt` — host activity with NavController
- [ ] `MilkEntryFragment.kt` — real-time entry form
- [ ] `CustomerListFragment.kt` — customer list with search
- [ ] `CustomerProfileFragment.kt` — ledger history view
- [ ] `ReportFragment.kt` — report generation UI
- [ ] XML layouts for all screens
- [ ] `res/xml/file_paths.xml` — FileProvider config
- [ ] `res/values/themes.xml` — Material Design theme
- [ ] `PaymentRepository.kt`
- [ ] Unit tests for `MilkStandardCalculator`

---

## Key Business Logic

### SNF Formula (FR-2.2)
```
SNF = (CLR / 4) + (0.2 × Fat%) + 0.36
```

### Total Amount (FR-3.3)
```
Total = Quantity (liters) × Rate per liter
```
Rate is dynamically looked up from the RateChart table based on Fat% and SNF%.

### WhatsApp Reminder (FR-8.1, FR-8.2)
Uses Android Intent with `https://wa.me/<phone>?text=<message>` URI scheme.

### Excel Export (FR-7.1, FR-7.2)
Uses Apache POI to write `.xlsx` to the Downloads directory, then triggers the Android share sheet.

---

## Database Schema

| Table | Primary Key | Key Columns |
|---|---|---|
| `customers` | `customerId` | name, phone, currentBalance |
| `milk_entries` | `entryId` | customerId, shift, qty, fat, snf, rate, total |
| `payments` | `paymentId` | customerId, amount, date, mode |
| `rate_chart` | `rateId` | minFat, maxFat, minSnf, maxSnf, ratePerLiter |

---

## SRS Compliance

| Requirement | Status |
|---|---|
| FR-1.x Milk Collection Entry | ✅ MilkEntry entity + DAO + Repository |
| FR-2.x SNF Calculator | ✅ MilkStandardCalculator.kt |
| FR-3.x Rate Calculation | ✅ RateChart entity + lookup query |
| FR-4.x Customer Ledger | ✅ Customer entity + balance tracking |
| FR-5.x Payment Tracking | ✅ Payment entity + DAO |
| FR-7.x Excel Export | ✅ ExcelExporter.kt |
| FR-8.x WhatsApp Reminder | ✅ WhatsAppHelper.kt |
| NFR – MVVM Architecture | ✅ ViewModels + Repository pattern |
| NFR – Offline First | ✅ Room local DB, no network required |
| NFR – Android 8.0+ | ✅ minSdk 26 in build.gradle |
