manage_instance.zip: manage_instance/manage_instance.py
	cd manage_instance && zip -u $@ manage_instance.py
	mv manage_instance/$@ ./
