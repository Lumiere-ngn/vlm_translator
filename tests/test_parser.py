from vlm_translator.ontario_laws import filter_laws, parse_part_x_laws


FIXTURE_HTML = """
<div>
  <p class="partnum"><a name="BK229"></a>PART X <br> RULES OF THE ROAD</p>
  <p class="headnote">Definitions, Part X</p>
  <p class="section"><a name="BK230"></a><b>133 </b>In this Part,</p>
  <p class="definition">"traffic control signal" means a signal.</p>
  <p class="footnoteLeft amendments collapsed">Section Amendments with date in force</p>
  <p class="headnote">Direction of traffic by police officer</p>
  <p class="section"><a name="BK231"></a><b>134 </b>(1) A police officer may direct traffic.</p>
  <p class="paragraph">(a) to ensure orderly movement of traffic;</p>
  <p class="headnote">Highway closing</p>
  <p class="subsection">(2) An officer may close a highway.</p>
  <p class="Ysection"><a name="BK232"></a><b>135 </b>Future text should be skipped.</p>
  <p class="headnote">Contracts of carriage</p>
  <p class="section"><a name="BK298"></a><b>191.0.1 </b>A contract provision is void.</p>
  <p class="partnum"><a name="BK299"></a>PART X.1 <br> TOLL HIGHWAYS</p>
  <p class="section"><a name="BK300"></a><b>191.1 </b>Do not include this.</p>
</div>
"""


def test_parse_part_x_laws_skips_future_and_stops_before_part_x_1():
    laws = parse_part_x_laws(FIXTURE_HTML)

    assert [law.section_number for law in laws] == ["133", "134", "191.0.1"]
    assert laws[0].title == "Definitions, Part X"
    assert laws[1].title == "Direction of traffic by police officer"
    assert "Section Amendments" not in laws[0].content
    assert "Future text" not in "\n".join(law.content for law in laws)
    assert "Highway closing" in laws[1].content
    assert "191.1" not in "\n".join(law.content for law in laws)


def test_filter_laws_empty_sections_means_all():
    laws = parse_part_x_laws(FIXTURE_HTML)

    assert filter_laws(laws, []) == laws
    assert [law.section_number for law in filter_laws(laws, ["134"])] == ["134"]
