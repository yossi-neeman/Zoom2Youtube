package com.neeman.zoom2youtube.data

data class Seder(val name: String, val masechtot: List<String>)

/** Same list and order as the web UI's מסכת dropdown. */
val SEDARIM = listOf(
    Seder("סדר זרעים", listOf("ברכות", "פאה", "דמאי", "כלאים", "שביעית", "תרומות", "מעשרות", "מעשר שני", "חלה", "ערלה", "בכורים")),
    Seder("סדר מועד", listOf("שבת", "עירובין", "פסחים", "שקלים", "יומא", "סוכה", "ביצה", "ראש השנה", "תענית", "מגילה", "מועד קטן", "חגיגה")),
    Seder("סדר נשים", listOf("יבמות", "כתובות", "נדרים", "נזיר", "סוטה", "גיטין", "קידושין")),
    Seder("סדר נזיקין", listOf("בבא קמא", "בבא מציעא", "בבא בתרא", "סנהדרין", "מכות", "שבועות", "עדויות", "עבודה זרה", "אבות", "הוריות")),
    Seder("סדר קדשים", listOf("זבחים", "מנחות", "חולין", "בכורות", "ערכין", "תמורה", "כריתות", "מעילה", "תמיד", "מדות", "קינים")),
    Seder("סדר טהרות", listOf("כלים", "אהלות", "נגעים", "פרה", "טהרות", "מקוואות", "נדה", "מכשירין", "זבים", "טבול יום", "ידים", "עוקצים")),
)

const val SYNAGOGUE_NAME = "בית כנסת נריה"

/** Format: מסכת | דף | בית כנסת נריה */
fun videoTitle(masechet: String, daf: String) = "$masechet | $daf | $SYNAGOGUE_NAME"

/** Format: מסכת - דף */
fun thumbnailText(masechet: String, daf: String) = "$masechet - $daf"
