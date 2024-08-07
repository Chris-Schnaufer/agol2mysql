drop function mapynu;

DELIMITER //
create function mapynu(ynu varchar(10))
returns varchar(10) DETERMINISTIC
BEGIN
  declare result varchar(10);
  if strcmp(lower(ynu), 'y') = 0 or
	  strcmp(lower(ynu), 'yes') = 0 then
    set result = 'Yes';
  elseif strcmp(lower(ynu), 'n') = 0 or
		 strcmp(lower(ynu), 'no') = 0 then
    set result = 'No';
  elseif ynu is null then
    set result = null;
  else
    set result = 'Unkn';
  end if;
  return result;
END//
DELIMITER ;

select mapynu('Y');
select mapynu('N');
select mapynu('U');
select mapynu('YES');
select mapynu('NO');
select mapynu(null);
select mapynu('UNKN');
