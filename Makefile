.PHONY: u10_teams u10_games u10_convert u10_rank u10_all
.PHONY: u11_teams u11_games u11_convert u11_rank u11_all
.PHONY: u12_teams u12_games u12_convert u12_rank u12_all
.PHONY: u13_teams u13_games u13_convert u13_rank u13_all
.PHONY: u14_teams u14_games u14_convert u14_rank u14_all

# U10 Pipeline
u10_teams:
	python src/scrapers/scraper_multi_division.py --division az_boys_u10 --mode teams

u10_games:
	python src/scrapers/scraper_multi_division.py --division az_boys_u10 --mode games

u10_convert:
	python src/utils/convert_to_ranking_format.py data/gold/Matched_Games_U10.csv data/gold/Matched_Games_U10_CLEAN.csv

u10_rank:
	python src/rankings/generate_team_rankings_v53_enhanced_multi.py \
		--division AZ_Boys_U10 \
		--input data/gold/Matched_Games_U10_CLEAN.csv \
		--output data/outputs/Rankings_AZ_M_U10_2025_v53e.csv

u10_all: u10_teams u10_games u10_convert u10_rank

# U11 Pipeline
u11_teams:
	python src/scrapers/scraper_multi_division.py --division az_boys_u11 --mode teams

u11_games:
	python src/scrapers/scraper_multi_division.py --division az_boys_u11 --mode games

u11_convert:
	python src/utils/convert_to_ranking_format.py data/gold/Matched_Games_U11.csv data/gold/Matched_Games_U11_CLEAN.csv

u11_rank:
	python src/rankings/generate_team_rankings_v53_enhanced_multi.py \
		--division AZ_Boys_U11 \
		--input data/gold/Matched_Games_U11_CLEAN.csv \
		--output data/outputs/Rankings_AZ_M_U11_2025_v53e.csv

u11_all: u11_teams u11_games u11_convert u11_rank

# U12 Pipeline
u12_teams:
	python src/scrapers/scraper_multi_division.py --division az_boys_u12 --mode teams

u12_games:
	python src/scrapers/scraper_multi_division.py --division az_boys_u12 --mode games

u12_convert:
	python src/utils/convert_to_ranking_format.py data/gold/Matched_Games_U12.csv data/gold/Matched_Games_U12_CLEAN.csv

u12_rank:
	python src/rankings/generate_team_rankings_v53_enhanced_multi.py \
		--division AZ_Boys_U12 \
		--input data/gold/Matched_Games_U12_CLEAN.csv \
		--output data/outputs/Rankings_AZ_M_U12_2025_v53e.csv

u12_all: u12_teams u12_games u12_convert u12_rank

# U13 Pipeline
u13_teams:
	python src/scrapers/scraper_multi_division.py --division az_boys_u13 --mode teams

u13_games:
	python src/scrapers/scraper_multi_division.py --division az_boys_u13 --mode games

u13_convert:
	python src/utils/convert_to_ranking_format.py data/gold/Matched_Games_U13.csv data/gold/Matched_Games_U13_CLEAN.csv

u13_rank:
	python src/rankings/generate_team_rankings_v53_enhanced_multi.py \
		--division AZ_Boys_U13 \
		--input data/gold/Matched_Games_U13_CLEAN.csv \
		--output data/outputs/Rankings_AZ_M_U13_2025_v53e.csv

u13_all: u13_teams u13_games u13_convert u13_rank

# U14 Pipeline
u14_teams:
	python src/scrapers/scraper_multi_division.py --division az_boys_u14 --mode teams

u14_games:
	python src/scrapers/scraper_multi_division.py --division az_boys_u14 --mode games

u14_convert:
	python src/utils/convert_to_ranking_format.py data/gold/Matched_Games_U14.csv data/gold/Matched_Games_U14_CLEAN.csv

u14_rank:
	python src/rankings/generate_team_rankings_v53_enhanced_multi.py \
		--division AZ_Boys_U14 \
		--input data/gold/Matched_Games_U14_CLEAN.csv \
		--output data/outputs/Rankings_AZ_M_U14_2025_v53e.csv

u14_all: u14_teams u14_games u14_convert u14_rank

# All divisions
all_divisions: u10_all u11_all u12_all u13_all u14_all

# Dashboard
dashboard:
	streamlit run src/dashboard/app_v53_multi_division.py

# Tests
test_u11:
	pytest -q tests/test_u11_pipeline.py

# Clean outputs
clean:
	rm -f data/outputs/Rankings_AZ_M_*_2025_v53e.csv
	rm -f data/outputs/connectivity_report_*_v53e.csv
	rm -f data/gold/Matched_Games_*_CLEAN.csv