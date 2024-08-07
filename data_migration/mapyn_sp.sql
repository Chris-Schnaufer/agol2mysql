drop function mapyn;

DELIMITER //
create function mapyn(yn varchar(10))
returns varchar(3) DETERMINISTIC
BEGIN
  declare result varchar(3);
  if strcmp(lower(yn), 'y') = 0 then
    set result = 'Yes';
  elseif yn is null then
    set result = null;
  else
    set result = 'No';
  end if;
  return result;
END//
DELIMITER ;

select mapyn('Y');
select mapyn('N');
select mapyn(null);