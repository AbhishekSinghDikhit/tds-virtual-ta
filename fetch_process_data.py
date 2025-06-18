from discourse_content.scrape_data import scrape_data
from discourse_content.filter_data import filter_data
from discourse_content.process_data import process_data
from course_content.scrape_data import scrape_tds_data
from course_content.process_data import process_tds_data


# Fetch, filter, and process discourse data.
scrape_data()
filter_data()
process_data()


# Fetch, filter, and process course data.
scrape_tds_data()
process_tds_data()

