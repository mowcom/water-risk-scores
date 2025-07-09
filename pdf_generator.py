from fpdf import FPDF
import pandas as pd

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Orphan Well Water Risk Dossier', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(5)

    def chapter_body(self, body):
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 10, body)
        self.ln()

    def add_table(self, data):
        self.set_font('Arial', 'B', 10)
        # Header
        for col_name in data.keys():
            self.cell(47, 10, col_name, 1)
        self.ln()
        # Data
        self.set_font('Arial', '', 10)
        for row in zip(*data.values()):
            for item in row:
                self.cell(47, 10, str(item), 1)
            self.ln()
        self.ln(10)

def generate_well_report(well_data):
    """Generates a PDF report for a single well."""
    pdf = PDF()
    pdf.add_page()

    # --- Well Details ---
    pdf.chapter_title(f"Well Dossier: {well_data['WELL_NAME']} (API: {well_data.name})")
    details_body = f"County: {well_data['COUNTY']}\nCompletion Year: {well_data['completion_year']}"
    pdf.chapter_body(details_body)

    # --- Risk Profile ---
    pdf.chapter_title("Risk Profile")
    risk_table_data = {
        'Metric': ['Final Score', 'Risk Tier', 'Leak Probability'],
        'Value': [f"{well_data['final_score']:.0f} / 100", well_data['risk_tier'], f"{well_data['P_Leak'] * 100:.1f}%"]
    }
    pdf.add_table(risk_table_data)

    # --- Component Breakdown ---
    pdf.chapter_title("Risk Component Breakdown")
    component_data = {
        'Component': ['Aquifer Vulnerability', 'Surface Water Proximity', 'Well Integrity (Age/Casing)', 'Historical Spills', 'Human Receptors'],
        'Score': [
            f"{well_data['aquifer_score']:.1f} / 30",
            f"{well_data['surface_water_score']:.1f} / 20",
            f"{well_data['casing_age_score']:.1f} / 20",
            f"{well_data['spill_score']:.1f} / 15",
            f"{well_data['receptors_score']:.1f} / 15"
        ]
    }
    pdf.add_table(component_data)

    # --- Water Safeguarded ---
    pdf.chapter_title("Water Safeguarded Metrics")
    water_body = f"By plugging this well, an estimated {well_data['Water_Safeguarded_m3_yr']:.1f} cubic meters/year ({well_data['Water_Safeguarded_acft_yr']:.2f} acre-feet/year) of freshwater are safeguarded from potential contamination."
    pdf.chapter_body(water_body)

    # --- AI Credit Buyer Summary ---
    pdf.chapter_title("AI Infrastructure Water Footprint Offset Certificate")
    ai_summary = (
        f"This certificate verifies that by funding the plugging of orphan well {well_data['WELL_NAME']} (API: {well_data.name}), "
        f"your organization has directly contributed to safeguarding freshwater resources. This action serves as a tangible, "
        f"measurable offset to the water footprint of your AI and data center operations.\n\n"
        f"**Verified Impact:**\n"
        f"- **Water Safeguarded:** A total of **{well_data['Water_Safeguarded_acft_yr']:.2f} acre-feet per year** of freshwater has been protected.\n"
        f"- **AI Operations Equivalent:** This volume is equivalent to the water required for approximately **{well_data['AI_gpt4_queries_per_year']:,}** complex GPT-4 queries per year.\n\n"
        f"By retiring the environmental risk posed by this well, you are ensuring the long-term integrity of local water supplies, "
        f"demonstrating a commitment to sustainable AI practices, and generating positive environmental, social, and governance (ESG) impact."
    )
    pdf.chapter_body(ai_summary)

    # --- Map ---
    pdf.add_page()
    pdf.chapter_title("Geographic Risk Map")
    map_path = f"output/{well_data['API']}_map.png"
    try:
        pdf.image(map_path, x=10, y=None, w=190)
    except RuntimeError:
        pdf.chapter_body("Map image not found. Please ensure analysis has been run.")

    # --- Save PDF ---
    output_path = f"output/{well_data['API']}_report.pdf"
    pdf.output(output_path)
    return output_path
