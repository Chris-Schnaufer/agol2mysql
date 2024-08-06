drop function mapcloud;

DELIMITER //
create function mapcloud(cloud varchar(50))
returns varchar(10) DETERMINISTIC
BEGIN
  declare result varchar(10);
  if strcmp(lower(cloud), '76_100') = 0 or 
     strcmp(lower(cloud), '75-100%') = 0 then
    set result = '76-100';
  elseif strcmp(lower(cloud), 'High-thin overcast') = 0 then
	set result = 'high_thin';
  elseif cloud is null then
    set result = null;
  else
    set result = lower(cloud);
  end if;
  return result;
END//
DELIMITER ;

select mapcloud(null);
select mapcloud('1_25');
select mapcloud('26_50');
select mapcloud('51_75');
select mapcloud('Fog');
select mapcloud('None');
select mapcloud('76_100');
select mapcloud('high_thin');
select mapcloud('High-thin overcast');
select mapcloud('75-100%');
