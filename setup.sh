sudo cp agents_cardio.conf /etc/supervisor/conf.d/
sudo cp agents_cardio_nginx.conf /etc/nginx/sites-available/
sudo supervisorctl update
sudo systemctl restart nginx
sudo certbot --nginx -d cardio.new.medsenger.ru