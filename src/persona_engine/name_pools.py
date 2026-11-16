"""Fixed synthetic name pools.

Every generated persona draws its first and last name from these committed
lists. Generating only from committed pools is what guarantees no generated
name references a real member identity: nothing outside these lists can
ever appear.
"""

FIRST_NAMES = (
    "Aiden", "Alice", "Amara", "Andrew", "Asha", "Beatrice", "Benjamin",
    "Carlos", "Chen", "Clara", "Dana", "Diego", "Edith", "Elena", "Elias",
    "Fatima", "Felix", "George", "Grace", "Hana", "Henry", "Ivan", "Jamal",
    "June", "Kai", "Katherine", "Leila", "Leon", "Lena", "Marcus",
    "Margaret", "Maya", "Milan", "Naomi", "Nikhil", "Nora", "Oliver",
    "Priya", "Quinn", "Rafael", "Rosa", "Samuel", "Sana", "Sofia",
    "Stefan", "Talia", "Theodore", "Uma", "Vera", "Victor", "Walter",
    "Yara", "Yusuf", "Zoe",
)

LAST_NAMES = (
    "Aber", "Alvarez", "Ashwood", "Barlow", "Bellamy", "Cardoso", "Chu",
    "Cohen", "Davies", "Delgado", "Dupont", "Ellery", "Farrow", "Ferreira",
    "Gale", "Grimshaw", "Hale", "Hartline", "Hern", "Iqbal", "Iversen",
    "Janssen", "Karn", "Kovac", "Larkin", "Lindqvist", "Mabry", "Marino",
    "Nguyen", "North", "Okafor", "Ostrow", "Pemberton", "Quintana",
    "Redner", "Roache", "Sandoval", "Sever", "Tanaka", "Thorn", "Ulrich",
    "Vance", "Varga", "Whitlock", "Xiang", "Yarrow", "Zadak", "Zeller",
)
