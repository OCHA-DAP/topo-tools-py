---
title: "1. Schema"
---

First step of boundary cleaning. A source delivery arrives with its own
column names. This step maps every level's names and codes to the
release schema (`adm{n}_name`, `adm{n}_code`) and copies each parent's
columns onto its children.

<div class="grid cards" markdown>

-   :material-school:{ .lg .middle } **Tutorial**

    ---

    Learning-oriented. Map one file's columns, copy ancestor columns
    from a join layer, then fill the hierarchy down.

    [:octicons-arrow-right-24: Tutorial](tutorial.md)

-   :material-hammer-wrench:{ .lg .middle } **How-to**

    ---

    Task-oriented. Map each level below admin0, review the crosswalk,
    then join each parent onto its children.

    [:octicons-arrow-right-24: How-to](how-to.md)

-   :material-book-open-variant:{ .lg .middle } **Reference**

    ---

    Information-oriented. What `schema-map`, `schema-join` and
    `schema-fill` do, with their options and outputs.

    [:octicons-arrow-right-24: Reference](reference/schema_map.md)

-   :material-lightbulb-on-outline:{ .lg .middle } **Explanation**

    ---

    Understanding-oriented. How levels are detected from the data rather
    than from column names, and how each schema tool uses that.

    [:octicons-arrow-right-24: Explanation](explanation/overview.md)

</div>
