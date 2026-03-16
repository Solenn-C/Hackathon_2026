silver:
	python src/scripts/silver_gold/run_pipeline.py

bronze:
	python src/scripts/bronze_silver/pipeline.py

get-data:
	python src/scripts/bronze_silver/pipeline.py
	python src/scripts/silver_gold/run_pipeline.py
