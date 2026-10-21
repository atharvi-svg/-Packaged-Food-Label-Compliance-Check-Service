
import json
import subprocess
import sys

import streamlit as st

st.set_page_config(
    page_title="Food Label Screening",
    page_icon="🥫",
    layout="wide",
)

st.title("🥫 Packaged Food Label Screening")
st.write(
    "Paste the text from a packaged food label to screen for "
    "label declarations and nutrition claims."
)

st.warning(
    "Screening prototype only. Results do not establish FSSAI "
    "compliance. Manual review is required."
)

label_text = st.text_area(
    "Food label text",
    height=220,
    placeholder=(
        "Product Name: High-Protein Sugar-Free Snack\n"
        "Ingredients: oats, whey protein, sweetener\n"
        "Nutrition Information: Protein 20 g, Sugars 0 g\n"
        "Net Quantity: 50 g\n"
        "Best Before: 6 months\n"
        "Manufactured by: Example Foods\n"
        "FSSAI Licence No. 12345678901234"
    ),
)

top_k = st.number_input(
    "Regulatory passages per query",
    min_value=1,
    max_value=10,
    value=3,
    step=1,
)

if st.button("Screen label", type="primary"):
    if not label_text.strip():
        st.error("Please enter some food label text.")
    else:
        with st.spinner("Screening label and retrieving references..."):
            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "src.compliance",
                        "--label",
                        label_text,
                        "--top-k",
                        str(int(top_k)),
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                report = json.loads(result.stdout)

                st.subheader("Screening result")
                st.info(report["overall_status"])

                summary = report["summary"]
                col1, col2, col3 = st.columns(3)

                col1.metric(
                    "Text checks detected",
                    summary["text_checks_detected"],
                    f'of {summary["text_checks_total"]}',
                )
                col2.metric(
                    "Not detected",
                    summary["text_checks_not_detected"],
                )
                col3.metric(
                    "Claims detected",
                    summary["claims_detected"],
                )

                st.subheader("Label text checks")
                st.dataframe(
                    report["findings"],
                    use_container_width=True,
                    hide_index=True,
                )

                st.subheader("General labelling references")
                if report["general_labelling_references"]:
                    for ref in report["general_labelling_references"]:
                        with st.expander(ref.get("citation") or "Reference"):
                            st.write(ref.get("excerpt", ""))
                else:
                    st.write("No references were retrieved.")

                st.subheader("Nutrition claim reviews")
                for claim in report["claim_reviews"]:
                    with st.expander(claim["claim"]):
                        st.write(claim["status"])
                        st.write(claim["review_note"])

                        refs = claim["regulatory_references"]
                        if refs:
                            for ref in refs:
                                st.markdown(
                                    f'**{ref.get("citation") or "Reference"}**'
                                )
                                st.write(ref.get("excerpt", ""))
                        else:
                            st.write(
                                "No references retrieved for this claim. "
                                "Manual review is required."
                            )

                st.caption(report["disclaimer"])

                st.download_button(
                    "Download report as JSON",
                    data=json.dumps(
                        report,
                        indent=2,
                        ensure_ascii=False,
                    ),
                    file_name="food_label_screening_report.json",
                    mime="application/json",
                )

            except subprocess.CalledProcessError as exc:
                st.error("The screening command failed.")
                st.code(exc.stderr or exc.stdout or str(exc))
            except json.JSONDecodeError:
                st.error("The screening output was not valid JSON.")