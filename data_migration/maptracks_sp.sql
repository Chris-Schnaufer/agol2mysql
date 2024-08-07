drop function maptracks;

DELIMITER //
create function maptracks(tracks varchar(50))
returns integer DETERMINISTIC
BEGIN
  declare result integer;
  if strcmp(lower(tracks), 'abundant') = 0 then
    set result = 6;
  elseif strcmp(lower(tracks), 'few') = 0 then
	set result = 3;
  elseif strcmp(lower(tracks), 'many') = 0 then
	set result = 5;
  elseif strcmp(lower(tracks), 'none') = 0 then
	set result = 0;
  elseif strcmp(lower(tracks), 'scarce') = 0 then
	set result = 1;
  else
    set result = cast(tracks as signed integer);
  end if;
  return result;
END//
DELIMITER ;

select maptracks('abundant');
select maptracks('few');
select maptracks('many');
select maptracks('none');
select maptracks('scarce');
select maptracks('0');
